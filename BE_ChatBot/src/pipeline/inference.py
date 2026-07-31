"""
History-Aware Travel Inference

FLOW:
  User question
      -> QueryRouter (language + travel intent + passport context)
      -> fast reply / ask passport country / deterministic visa reply
      -> direct LLM answer for general travel questions
      -> Orchestrator in recommendation or trip_planning mode
      -> LLM natural-language answer
      -> append verified visa note and trip JSON when applicable
      -> save the complete turn to session history
"""

import asyncio
import json
import os
import re
from collections import defaultdict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.core.llm_container import get_llm, get_model_info, get_system_prompt

from ..core.base_llm_model import LLMProvider
from ..services.visa_advisor import VisaAdvisor

# Import các module
from .orchestrator import TripOrchestrator
from .query_router import QueryRouter, RouteDecision, RoutingContext

# Limit turns tránh vượt quá context window LLM
_MAX_HISTORY_TURNS = 10  # 1 turn = 1 HumanMessage + 1 AIMessage


class RAGInference:
    def __init__(self):
        print("\n⚙️ Đang khởi tạo RAG Inference Pipeline")

        # ========= COMPONENTS =========
        print("\n- LLM cho response user (core)")
        self.llm = get_llm()  # LLM chạy chain (core)

        print("\n- LLM cho rewrite question (hisory chat)")
        self.llm_rewrite = get_llm(
            LLMProvider(os.getenv("REWRITE_LLM_PROVIDER")),
            model_name=os.getenv("REWRITE_LLM_MODEL") or None,
            temperature=0.2,
        )  # LLM rewrite

        # Query Router => language, domain, travel task and passport context.
        self.visa_advisor = VisaAdvisor()
        self.query_router = QueryRouter(
            llm=self.llm_rewrite,
            passport_country_resolver=self.visa_advisor.resolve_passport_country,
        )

        # Orchestrator: MultiQuery -> DocumentReranker -> reranked docs
        self.orchestrator = TripOrchestrator(llm=self.llm)
        self.system_prompt = get_system_prompt()  # System prompt
        self.model_info_core = get_model_info(self.llm)

        # ------------------------------------------------------------------ #
        # Chat history store: { session_id → [HumanMessage, AIMessage, ...] }
        # Dùng defaultdict(list) => không cần khởi tạo thủ công từng session.
        # ------------------------------------------------------------------ #
        self._history: dict[str, list] = defaultdict(list)
        self._routing_context: dict[str, RoutingContext] = defaultdict(RoutingContext)
        self._pending_timing_question: dict[str, str] = {}
        """
        RAM self._history
        → dùng để chat nhanh trong runtime hiện tại

        DB conversations + messages
        → dùng để persist qua restart/shutdown

        hydrate_history()
        → cầu nối DB messages → RAM self._history
        """

        self.model_info_rewrite = get_model_info(self.llm_rewrite)

    def _get_history(self, session_id: str) -> list:
        """Trả về lịch sử hội thoại dựa vào session_id (cắt bớt nếu quá dài)."""
        history = self._history[session_id]

        # Giữ lại _MAX_HISTORY_TURNS turns gần nhất (Tối đa 10 lượt)
        # Mỗi turn = 2 message
        max_messages = _MAX_HISTORY_TURNS * 2  # 1 HumanMessage + 1 AIMessage

        return history[-max_messages:] if len(history) > max_messages else history

    # Viết lại câu hỏi dựa trên history
    async def _rewrite_question(
        self,
        question: str,
        history: list,
        response_language: str = "vi",
    ) -> str:
        """
        Nếu có history, viết lại câu hỏi hiện tại thành truy vấn độc lập.
        Chỉ dùng history rút gọn để tránh assistant answer dài/JSON làm LLM rewrite
        bị trôi thành câu trả lời.
        """
        if not history:
            return question

        user_turns = []
        assistant_hints = []

        for message in history[-8:]:
            content = str(getattr(message, "content", "")).strip()
            if not content:
                continue

            if isinstance(message, HumanMessage):
                user_turns.append(HumanMessage(content=content[:500]))
                continue

            if isinstance(message, AIMessage):
                content = re.sub(
                    r"```json[\s\S]*?```",
                    "",
                    content,
                    flags=re.IGNORECASE,
                ).strip()
                content = re.sub(r"```[\s\S]*?```", "", content).strip()
                content = re.sub(r"\{[\s\S]*\}", "", content).strip()
                if content:
                    assistant_hints.append(AIMessage(content=content[:250]))

        compact_history = user_turns[-4:]
        if not compact_history:
            compact_history = assistant_hints[-1:]

        target_language = "English" if response_language == "en" else "Vietnamese"
        messages = (
            [
                SystemMessage(
                    content=(
                        f"Rewrite the user's new travel question into ONE short standalone {target_language} travel query.\n"
                        "Use previous USER messages to recover destination, days, budget, dates, group size, and preferences.\n"
                        "If the conversation is about an itinerary, rewrite every follow-up as a complete itinerary request that preserves the original trip constraints and includes the requested adjustment.\n"
                        "Do NOT answer the question.\n"
                        "Do NOT create an itinerary.\n"
                        "Do NOT include markdown, JSON, bullets, explanations, or suggestions.\n"
                        "Return only the rewritten query."
                    )
                )
            ]
            + compact_history
            + [HumanMessage(content=f"New question: {question}")]
        )

        result = await self.llm_rewrite.ainvoke(messages)
        rewritten = result.content.strip()

        invalid_rewrite = (
            not rewritten
            or len(rewritten) > 300
            or "```" in rewritten
            or rewritten.startswith(("{", "["))
            or "###" in rewritten
            or "```json" in rewritten.lower()
            or "dưới đây" in rewritten.lower()
        )

        if invalid_rewrite:
            print(
                f"\n⚠️ Rewrite không hợp lệ, dùng lại câu hỏi gốc bởi [{self.model_info_rewrite}]:"
            )
            print(f"   {question}")
            return question

        print(f"\n🔄 Viết lại câu hỏi (history chat) bởi [{self.model_info_rewrite}]:")
        print(f"   {rewritten}")
        return rewritten

    def _build_messages(
        self,
        history: list,
        context: str,
        question: str,
        itinerary_text: str = None,
        weather_context: str = "",
        budget_context: str = "",
        response_language: str = "vi",
        execution_mode: str = "trip_planning",
    ) -> list:
        """
        Ghép prompt hoàn chỉnh:
          SystemMessage (system_prompt + hướng dẫn + context)
          + history (HumanMessage + AIMessage xen kẽ)
          + HumanMessage (câu hỏi hiện tại)
        """
        language_instruction = (
            "Respond in English."
            if response_language == "en"
            else "Trả lời bằng tiếng Việt."
        )
        system_content = f"""{self.system_prompt}

    RESPONSE LANGUAGE: {language_instruction}
    EXECUTION MODE: {execution_mode}"""

        if weather_context:
            # Weather context giup LLM can nhac yeu to thuc tien khi tu van nen di hay can doi lich.
            system_content += f"""

    THÔNG TIN THỜI TIẾT / KHÍ HẬU THỰC TIỄN:
    {weather_context}

    Khi tư vấn, hãy dùng phần này để nói rõ nên đi, nên cân nhắc, hoặc nên đổi lịch nếu rủi ro thời tiết cao."""

        if budget_context:
            system_content += f"""

    THÔNG TIN NGÂN SÁCH MINH BẠCH:
    {budget_context}"""

        if itinerary_text:
            system_content += f"""

    Dưới đây là LỊCH TRÌNH DU LỊCH TỐI ƯU đã được các thuật toán đồ thị (Dijkstra/Greedy) tính toán sẵn. Hãy trình bày tự nhiên bằng ngôn ngữ phản hồi đã chỉ định và KHÔNG tự ý thay đổi thứ tự địa điểm hoặc thời gian:
    {itinerary_text}"""

        if context:
            system_content += f"""

    Ngữ cảnh thông tin chi tiết các địa điểm:
    {context}"""

        system_content += """

    LƯU Ý: Không tự tạo quy định visa và không tạo khối JSON. Backend sẽ đính kèm visa note và JSON lịch trình khi phù hợp."""

        return (
            [SystemMessage(content=system_content)]
            + history
            + [HumanMessage(content=question)]
        )

    def _format_itinerary_for_llm(self, plan) -> str:
        """
        Chuyển TripPlan thành dạng text tóm tắt để LLM biết lịch trình tối ưu thực tế
        và viết lời giới thiệu tự nhiên.
        """
        if not plan or not plan.days:
            return "Không có lịch trình được lập."

        lines = []
        lines.append(
            f"Hành trình: {plan.trip_request.region or ''} ({plan.trip_request.days or 0} ngày)"
        )
        for day_plan in plan.days:
            lines.append(f"\nNgày {day_plan.day}:")
            for sp in day_plan.places:
                lines.append(
                    f"  - [{sp.arrival_time} - {sp.departure_time}] {sp.place.name}"
                )
        return "\n".join(lines)

    def _format_weather_for_llm(self, weather) -> str:
        """
        Chuyen WeatherAdvice thanh context ngan de LLM dung khi tu van co nen di hay khong.
        """
        if not weather:
            return ""

        risk_label = {
            "low": "thấp",
            "medium": "trung bình",
            "high": "cao",
            "mixed": "phụ thuộc ngày đi",
        }.get(weather.risk_level, weather.risk_level)
        should_go_label = {
            "recommended": "nên đi",
            "go_with_caution": "có thể đi nhưng cần chuẩn bị",
            "not_recommended": "không nên đi",
            "depends_on_date": "cần ngày đi cụ thể hơn",
        }.get(weather.should_go, weather.should_go)

        lines = [
            weather.summary,
            f"Mức rủi ro thời tiết: {risk_label}",
            f"Khuyến nghị: {should_go_label}",
            f"Nguồn dữ liệu: {weather.data_source}",
        ]
        if weather.reasons:
            lines.append("Lý do: " + "; ".join(weather.reasons))
        if weather.suggestions:
            lines.append("Gợi ý thực tiễn: " + "; ".join(weather.suggestions))

        return "\n".join(lines)

    def _build_visa_note(
        self,
        routing_context: RoutingContext,
        route_decision: RouteDecision,
        trip_request=None,
        force: bool = False,
    ) -> str:
        passport_country = (
            route_decision.passport_country or routing_context.passport_country
        )
        if not passport_country or self.visa_advisor.is_vietnamese(passport_country):
            return ""

        stay_days = route_decision.stay_days
        entry_date = route_decision.entry_date
        if trip_request is not None:
            stay_days = getattr(trip_request, "days", None) or stay_days
            start_date = getattr(trip_request, "start_date", None)
            entry_date = str(start_date) if start_date else entry_date

        advice = self.visa_advisor.get_advice(
            passport_country=passport_country,
            stay_days=stay_days,
            entry_date=entry_date,
        )
        if not force and routing_context.visa_note_signature == advice.signature:
            return ""

        routing_context.visa_note_signature = advice.signature
        return advice.render(route_decision.response_language)

    def _build_json_block(
        self,
        trip_plan,
        response_language: str = "vi",
    ) -> str:
        if not trip_plan:
            return ""
        serialized_plan = self.orchestrator._trip_plan_to_dict(
            trip_plan,
            response_language=response_language,
        )
        return (
            "\n\n```json\n"
            + json.dumps(serialized_plan, ensure_ascii=False, indent=2)
            + "\n```"
        )

    def _build_timing_advice(
        self,
        trip_plan,
        response_language: str = "vi",
    ) -> str:
        advice = getattr(trip_plan, "timing_advice", None)
        if advice is None:
            return ""
        return self.orchestrator.travel_timing_service.render_markdown(
            advice,
            response_language,
        )

    def _build_recommendation_details(
        self,
        places: list,
        response_language: str = "vi",
    ) -> str:
        """Build deterministic recommendation reasons without asking the LLM."""
        if not places:
            return ""

        language = "en" if response_language == "en" else "vi"
        heading = (
            "### Why these places were recommended"
            if language == "en"
            else "### Vì sao các địa điểm này được đề xuất"
        )
        lines = [heading]
        display_index = 0

        for place in places:
            details = self.orchestrator._place_recommendation_to_dict(
                place,
                language,
            )
            reasons = details["recommendation_reasons"]
            if not reasons:
                continue

            display_index += 1
            lines.append(f"\n**{display_index}. {details['name']}**")
            lines.extend(f"- {reason}" for reason in reasons)

        if len(lines) == 1:
            return ""
        return "\n\n" + "\n".join(lines)

    def _format_vnd(self, amount: float, language: str) -> str:
        formatted_amount = f"{round(float(amount or 0)):,}"
        if language != "en":
            formatted_amount = formatted_amount.replace(",", ".")
        return f"{formatted_amount} VND"

    def _format_budget_for_llm(
        self,
        budget_summary: dict | None,
        response_language: str = "vi",
    ) -> str:
        """Provide verified fee scope so the LLM does not claim full affordability."""
        if not budget_summary:
            return ""

        language = "en" if response_language == "en" else "vi"
        requested_budget = self._format_vnd(
            budget_summary["requested_budget"],
            language,
        )
        estimated_total = self._format_vnd(
            budget_summary["estimated_entrance_fee_total"],
            language,
        )
        known_count = budget_summary["known_fee_place_count"]
        total_count = budget_summary["total_place_count"]
        unclassified_count = budget_summary["unclassified_fee_place_count"]
        if known_count == 0:
            estimated_total = (
                "No classified entrance-fee data"
                if language == "en"
                else "Chưa có dữ liệu phí được phân loại"
            )

        if language == "en":
            return (
                f"Requested total budget: {requested_budget}.\n"
                f"Known entrance-fee estimate: {estimated_total}.\n"
                f"Fee coverage: {known_count}/{total_count} places; "
                f"{unclassified_count} places have unclassified fees.\n"
                "These figures cover known entrance fees only. Never claim that the "
                "whole trip fits the budget because accommodation, food, transport, "
                "and incidental costs are not included."
            )
        return (
            f"Ngân sách tổng đã cung cấp: {requested_budget}.\n"
            f"Phí tham quan đã biết ước tính: {estimated_total}.\n"
            f"Mức độ bao phủ phí: {known_count}/{total_count} địa điểm; "
            f"{unclassified_count} địa điểm chưa phân loại phí.\n"
            "Các số liệu này chỉ bao gồm phí tham quan đã biết. Không được kết luận "
            "toàn bộ chuyến đi nằm trong ngân sách vì chưa tính lưu trú, ăn uống, "
            "di chuyển và chi phí phát sinh."
        )

    def _build_budget_details(
        self,
        budget_summary: dict | None,
        response_language: str = "vi",
    ) -> str:
        """Build the recommendation-mode budget disclosure deterministically."""
        if not budget_summary:
            return ""

        language = "en" if response_language == "en" else "vi"
        requested_value = budget_summary["requested_budget"]
        estimated_value = budget_summary["estimated_entrance_fee_total"]
        requested_budget = self._format_vnd(requested_value, language)
        estimated_total = self._format_vnd(estimated_value, language)
        known_count = budget_summary["known_fee_place_count"]
        total_count = budget_summary["total_place_count"]
        unclassified_count = budget_summary["unclassified_fee_place_count"]
        status = budget_summary["status"]
        if known_count == 0:
            estimated_total = (
                "No classified entrance-fee data"
                if language == "en"
                else "Chưa có dữ liệu phí được phân loại"
            )

        if language == "en":
            lines = [
                "### Budget transparency",
                "",
                f"- **Requested budget:** {requested_budget}",
                f"- **Known entrance-fee estimate:** {estimated_total}",
                f"- **Fee coverage:** {known_count}/{total_count} places",
                f"- **Unclassified fees:** {unclassified_count} places",
                "",
            ]
            if status == "estimated_over_budget":
                over_amount = self._format_vnd(
                    estimated_value - requested_value,
                    language,
                )
                lines.append(
                    "Known entrance fees alone exceed the requested budget by "
                    f"approximately {over_amount}."
                )
            elif status == "partial":
                if known_count == 0:
                    lines.append(
                        "No entrance fees are currently classified, so there is "
                        "not enough data to assess the whole trip."
                    )
                else:
                    lines.append(
                        "Known entrance fees do not currently exceed the budget, but "
                        "there is not enough data to assess the whole trip."
                    )
            else:
                lines.append(
                    "The estimated entrance fees are within the requested budget."
                )
            lines.extend(
                [
                    "",
                    "> This estimate covers known entrance fees only; accommodation, "
                    "food, transport, and incidental costs are not included.",
                ]
            )
        else:
            lines = [
                "### Minh bạch ngân sách",
                "",
                f"- **Ngân sách đã cung cấp:** {requested_budget}",
                f"- **Tổng phí tham quan đã biết:** {estimated_total}",
                f"- **Dữ liệu phí:** {known_count}/{total_count} địa điểm",
                f"- **Chưa phân loại phí:** {unclassified_count} địa điểm",
                "",
            ]
            if status == "estimated_over_budget":
                over_amount = self._format_vnd(
                    estimated_value - requested_value,
                    language,
                )
                lines.append(
                    "Riêng phí tham quan đã biết đã vượt ngân sách khoảng "
                    f"{over_amount}."
                )
            elif status == "partial":
                if known_count == 0:
                    lines.append(
                        "Hiện chưa có phí tham quan nào được phân loại nên chưa đủ "
                        "dữ liệu để đánh giá toàn bộ chuyến đi."
                    )
                else:
                    lines.append(
                        "Phần phí tham quan đã biết hiện không vượt quá ngân sách. "
                        "Tuy nhiên, chưa đủ dữ liệu để đánh giá toàn bộ chuyến đi."
                    )
            else:
                lines.append("Phí tham quan ước tính nằm trong ngân sách đã cung cấp.")
            lines.extend(
                [
                    "",
                    "> Ước tính chỉ bao gồm phí tham quan đã biết; chưa bao gồm lưu trú, "
                    "ăn uống, di chuyển và chi phí phát sinh.",
                ]
            )

        return "\n\n" + "\n".join(lines)

    def _timeout_reply(self, language: str) -> str:
        if language == "en":
            return (
                "Sorry, the response model timed out. The request was routed, "
                "but the answer could not be generated. Please try again shortly."
            )
        return (
            "Xin lỗi, mô hình phản hồi đang bị timeout. "
            "Hệ thống đã định tuyến yêu cầu nhưng chưa thể tạo câu trả lời. "
            "Vui lòng thử lại sau ít phút."
        )

    def _domestic_visa_reply(self, language: str) -> str:
        if language == "en":
            return (
                "You confirmed that you will use a Vietnamese passport, so foreign-entry "
                "visa guidance does not apply. Check that the passport is valid for your trip."
            )
        return (
            "Bạn đã xác nhận sử dụng hộ chiếu Việt Nam nên hướng dẫn visa nhập cảnh "
            "dành cho người nước ngoài không áp dụng. Hãy kiểm tra hộ chiếu còn hiệu lực cho chuyến đi."
        )

    def _visa_route_closing(self, language: str) -> str:
        source_url = str(self.visa_advisor.sources.get("mofa") or "")
        if language == "en":
            return (
                "\n\n> **The data may contain errors; to be certain, please verify "
                "the information at the "
                f"[official Vietnam Ministry of Foreign Affairs source]({source_url}).**"
            )
        return (
            "\n\n> **Dữ liệu có thể có sai sót; để chắc chắn, bạn hãy kiểm tra lại "
            "thông tin tại "
            f"[nguồn chính thức của Bộ Ngoại giao Việt Nam]({source_url}).**"
        )

    def _restore_pending_context(self, session_id: str, history: list) -> None:
        routing_context = self._routing_context[session_id]
        if (
            routing_context.pending_question
            or self._pending_timing_question.get(session_id)
            or not history
        ):
            return

        last_message = history[-1]
        if not isinstance(last_message, AIMessage):
            return

        content = str(getattr(last_message, "content", "")).lower()
        is_timing_question = (
            "to calculate the departure time before creating the itinerary" in content
            or "\u0111\u1ec3 t\u00ednh gi\u1edd kh\u1edfi h\u00e0nh tr\u01b0\u1edbc khi t\u1ea1o itinerary"
            in content
        )
        if is_timing_question:
            routing_context.response_language = (
                "en" if content.startswith("to calculate") else "vi"
            )
            for previous in reversed(history[:-1]):
                if isinstance(previous, HumanMessage):
                    self._pending_timing_question[session_id] = str(previous.content)
                    return

        is_country_question = (
            "which country's passport" in content
            or "hộ chiếu do quốc gia nào" in content
        )
        if not is_country_question:
            return

        routing_context.response_language = (
            "en" if "which country's passport" in content else "vi"
        )
        for previous in reversed(history[:-1]):
            if isinstance(previous, HumanMessage):
                routing_context.pending_question = str(previous.content)
                return

    def _save_turn(self, session_id: str, question: str, answer: str) -> None:
        """Lưu lượt hội thoại vào history."""
        self._history[session_id].append(HumanMessage(content=question))
        self._history[session_id].append(AIMessage(content=answer))

    # Nap lsu tu DB => memory khi tiep tuc conversation cũ
    def hydrate_history(self, session_id: str, messages: list) -> None:
        """
        Load DB messages vao memory cua RAG
                ↓
        DB messages → HumanMessage / AIMessage
                ↓
        self._history[conversation_id] có lại context
                ↓
        predict_stream / predict_async
                ↓
        _rewrite_question() dùng được history cũ
        """

        # Neu memory co history trc do (BE chua restart & user dang chat cung session) => Ko nap
        if self._history[session_id]:
            return

        history = []

        # Luu msg = role => convert qua object LangChain (RAG needed)
        #
        for message in messages:
            if message.role == "user":
                history.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                history.append(AIMessage(content=message.content))

        self._history[session_id] = history
        self._restore_pending_context(session_id, history)

        # Helper cho Query Router

    def _build_fast_reply(self, route_decision) -> str:
        return (
            route_decision.reply or "Hệ thống hiện chỉ hỗ trợ tư vấn du lịch Việt Nam."
        )

    def _log_route_decision(self, route_decision: RouteDecision) -> None:
        print(
            "\n[Query Router] "
            f"intent={route_decision.intent}, "
            f"action={route_decision.action}, "
            f"language={route_decision.language}, "
            f"response_language={route_decision.response_language}, "
            f"confidence={route_decision.confidence:.2f}, "
            f"reason={route_decision.reason}"
        )

    async def _prepare_generation(
        self,
        question: str,
        history: list,
        route_decision: RouteDecision,
    ) -> dict:
        effective_question = route_decision.resolved_question or question

        if route_decision.action == "direct_answer":
            messages = self._build_messages(
                history=history,
                context="",
                question=effective_question,
                response_language=route_decision.response_language,
                execution_mode="travel_general",
            )
            return {
                "messages": messages,
                "trip_request": None,
                "trip_plan": None,
                "places": [],
                "budget_summary": None,
                "execution_mode": "travel_general",
            }

        if route_decision.resolved_question:
            search_question = effective_question
        else:
            search_question = await self._rewrite_question(
                effective_question,
                history,
                route_decision.response_language,
            )

        mode = (
            "recommendation"
            if route_decision.action == "run_recommendation"
            else "trip_planning"
        )
        orch_res = await self.orchestrator.run(
            search_question,
            mode=mode,
            response_language=route_decision.response_language,
        )
        clarification_reply = orch_res.get("clarification_reply")
        if clarification_reply:
            return {
                "messages": None,
                "trip_request": orch_res["trip_request"],
                "trip_plan": None,
                "places": [],
                "budget_summary": None,
                "execution_mode": mode,
                "clarification_reply": clarification_reply,
                "search_question": search_question,
            }
        relevant_places = orch_res["places"]
        trip_request = orch_res["trip_request"]
        trip_plan = orch_res["trip_plan"]
        weather = orch_res.get("weather")
        budget_summary = orch_res.get("budget_summary")

        place_context = "\n\n".join(
            place.description for place in relevant_places if place.description
        )
        itinerary_text = None
        if trip_plan and trip_plan.days:
            itinerary_text = self._format_itinerary_for_llm(trip_plan)

        messages = self._build_messages(
            history=history,
            context=place_context,
            question=effective_question,
            itinerary_text=itinerary_text,
            weather_context=self._format_weather_for_llm(weather),
            budget_context=self._format_budget_for_llm(
                budget_summary,
                route_decision.response_language,
            ),
            response_language=route_decision.response_language,
            execution_mode=mode,
        )
        return {
            "messages": messages,
            "trip_request": trip_request,
            "trip_plan": trip_plan,
            "places": relevant_places,
            "budget_summary": budget_summary,
            "execution_mode": mode,
            "clarification_reply": None,
            "search_question": search_question,
        }

    # ============================================================ #
    # PUBLIC API
    # ============================================================ #

    # ========= Hàm Async để gọi API =========
    async def predict_async(
        self,
        question: str,
        session_id: str = "default",
    ) -> str:
        """
        Main entry point — gọi từ FastAPI

        Args:
            question:   Câu hỏi của user.
            session_id: ID phiên chat (mỗi user/tab nên có ID riêng).
                        Mặc định "default" cho Gradio single-user.

        Returns:
            Câu trả lời dạng string.
        """
        history = self._get_history(session_id)
        pending_timing_question = self._pending_timing_question.get(session_id)
        pipeline_question = (
            f"{pending_timing_question}\nThông tin bổ sung: {question}"
            if pending_timing_question
            else question
        )
        routing_context = self._routing_context[session_id]
        route_decision = await self.query_router.route(
            pipeline_question,
            history,
            routing_context,
        )
        self._log_route_decision(route_decision)

        if route_decision.action in {"fast_reply", "ask_country"}:
            answer = self._build_fast_reply(route_decision)
            print(f"\n[Query Router] Fast reply ({route_decision.intent}): {answer}")
            self._save_turn(session_id, question, answer)
            return answer

        if route_decision.action == "visa_reply":
            answer = self._build_visa_note(
                routing_context,
                route_decision,
                force=True,
            ).lstrip()
            if not answer:
                answer = self._domestic_visa_reply(route_decision.response_language)
            answer += self._visa_route_closing(route_decision.response_language)
            self._save_turn(session_id, question, answer)
            return answer

        prepared = await self._prepare_generation(
            pipeline_question,
            history,
            route_decision,
        )
        if prepared.get("clarification_reply"):
            answer = prepared["clarification_reply"]
            self._pending_timing_question[session_id] = prepared["search_question"]
            self._save_turn(session_id, question, answer)
            return answer

        self._pending_timing_question.pop(session_id, None)
        try:
            result = await self.llm.ainvoke(prepared["messages"])
            answer = result.content
        except (TimeoutError, asyncio.TimeoutError) as exc:
            print(
                f"[RAGInference] LLM response failed: {type(exc).__name__}: {exc}",
                flush=True,
            )
            answer = self._timeout_reply(route_decision.response_language)

        if prepared["execution_mode"] == "recommendation":
            answer += self._build_recommendation_details(
                prepared["places"],
                route_decision.response_language,
            )
            answer += self._build_budget_details(
                prepared["budget_summary"],
                route_decision.response_language,
            )
        answer += self._build_visa_note(
            routing_context,
            route_decision,
            trip_request=prepared["trip_request"],
        )
        answer += self._build_timing_advice(
            prepared["trip_plan"],
            route_decision.response_language,
        )
        answer += self._build_json_block(
            prepared["trip_plan"],
            route_decision.response_language,
        )

        print(f"\n [{self.model_info_core}]: {answer}")
        self._save_turn(session_id, question, answer)
        return answer

    async def predict_stream(
        self,
        question: str,
        session_id: str = "default",
    ):
        """
        - Stream phản hồi kết hợp với việc giữ session id
        - Lay lich su cua sesseion cụ thể
        """
        history = self._get_history(session_id)
        pending_timing_question = self._pending_timing_question.get(session_id)
        pipeline_question = (
            f"{pending_timing_question}\nThông tin bổ sung: {question}"
            if pending_timing_question
            else question
        )
        routing_context = self._routing_context[session_id]
        route_decision = await self.query_router.route(
            pipeline_question,
            history,
            routing_context,
        )
        self._log_route_decision(route_decision)

        if route_decision.action in {"fast_reply", "ask_country"}:
            full_answer = self._build_fast_reply(route_decision)
            print(
                f"\n[Query Router] Fast stream reply ({route_decision.intent}): {full_answer}"
            )
            yield full_answer
            self._save_turn(session_id, question, full_answer)
            return

        if route_decision.action == "visa_reply":
            full_answer = self._build_visa_note(
                routing_context,
                route_decision,
                force=True,
            ).lstrip()
            if not full_answer:
                full_answer = self._domestic_visa_reply(
                    route_decision.response_language
                )
            full_answer += self._visa_route_closing(route_decision.response_language)
            yield full_answer
            self._save_turn(session_id, question, full_answer)
            return

        prepared = await self._prepare_generation(
            pipeline_question,
            history,
            route_decision,
        )
        if prepared.get("clarification_reply"):
            full_answer = prepared["clarification_reply"]
            self._pending_timing_question[session_id] = prepared["search_question"]
            yield full_answer
            self._save_turn(session_id, question, full_answer)
            return

        self._pending_timing_question.pop(session_id, None)
        full_answer = ""
        try:
            async for chunk in self.llm.astream(prepared["messages"]):
                token = getattr(chunk, "content", "")
                if token:
                    full_answer += token
                    yield token
        except (TimeoutError, asyncio.TimeoutError) as exc:
            print(
                f"[RAGInference] LLM stream failed: {type(exc).__name__}: {exc}",
                flush=True,
            )
            fallback_answer = "\n\n" + self._timeout_reply(
                route_decision.response_language
            )
            full_answer += fallback_answer
            yield fallback_answer

        if prepared["execution_mode"] == "recommendation":
            recommendation_details = self._build_recommendation_details(
                prepared["places"],
                route_decision.response_language,
            )
            if recommendation_details:
                full_answer += recommendation_details
                yield recommendation_details

            budget_details = self._build_budget_details(
                prepared["budget_summary"],
                route_decision.response_language,
            )
            if budget_details:
                full_answer += budget_details
                yield budget_details

        visa_note = self._build_visa_note(
            routing_context,
            route_decision,
            trip_request=prepared["trip_request"],
        )
        if visa_note:
            full_answer += visa_note
            yield visa_note

        timing_advice = self._build_timing_advice(
            prepared["trip_plan"],
            route_decision.response_language,
        )
        if timing_advice:
            full_answer += timing_advice
            yield timing_advice

        json_block = self._build_json_block(
            prepared["trip_plan"],
            route_decision.response_language,
        )
        if json_block:
            full_answer += json_block
            yield json_block

        print(f"\n [{self.model_info_core}]: {full_answer}")

        # [6] Lưu vào history
        self._save_turn(session_id, question, full_answer)

    # Xóa lịch sử - API
    def clear_history(self, session_id: str = "default") -> None:
        """Xóa lịch sử của một session (dùng cho nút 'New Chat')."""
        self._history.pop(session_id, None)
        self._routing_context.pop(session_id, None)
        self._pending_timing_question.pop(session_id, None)
        print(f"🗑️  History cleared for session: {session_id}")

    #
    def get_history_length(self, session_id: str = "default") -> int:
        """Trả về số lượt hội thoại (turns) của session."""
        return len(self._history[session_id]) // 2
