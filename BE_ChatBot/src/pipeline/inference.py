"""
History-Aware RAG Inference Pipeline
FLOW:
  User question
      ↓
  [1] Rewrite question thành standalone (nếu có history)
      ↓
  [2] Multi-Query Retrieval
        ↓ LLM sinh N variations
        ↓ Hybrid Search (Vector + BM25) với từng variation
        ↓ Deduplicate → List[Document]
      ↓
  [3] Build prompt = system + chat_history + context + question
      ↓
  [4] LLM generate answer
      ↓
  [5] Lưu (user_question, answer) vào history
      ↓
  Return answer ✅
"""

import os
import re
import json
import asyncio
from collections import defaultdict

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.core.llm_container import get_llm, get_system_prompt, get_model_info

# Import các module
from .orchestrator import TripOrchestrator
from ..core.base_llm_model import LLMProvider
from .query_router import QueryRouter

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

        # Query Router => Block question out of domain before run pipeline
        self.query_router = QueryRouter(llm=self.llm_rewrite)  # <= co the thay doi LLM

        # Orchestrator: MultiQuery -> DocumentReranker -> reranked docs
        self.orchestrator = TripOrchestrator(llm=self.llm)
        self.system_prompt = get_system_prompt()  # System prompt
        self.model_info_core = get_model_info(self.llm)

        # ------------------------------------------------------------------ #
        # Chat history store: { session_id → [HumanMessage, AIMessage, ...] }
        # Dùng defaultdict(list) => không cần khởi tạo thủ công từng session.
        # ------------------------------------------------------------------ #
        self._history: dict[str, list] = defaultdict(list)
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
    async def _rewrite_question(self, question: str, history: list) -> str:
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

        messages = (
            [
                SystemMessage(
                    content=(
                        "Rewrite the user's new travel question into ONE short standalone Vietnamese travel-planning query.\n"
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
    ) -> list:
        """
        Ghép prompt hoàn chỉnh:
          SystemMessage (system_prompt + hướng dẫn + context)
          + history (HumanMessage + AIMessage xen kẽ)
          + HumanMessage (câu hỏi hiện tại)
        """
        system_content = f"""{self.system_prompt}

    Hãy trả lời câu hỏi của người dùng dựa trên ngữ cảnh và thông tin địa điểm dưới đây."""

        if weather_context:
            # Weather context giup LLM can nhac yeu to thuc tien khi tu van nen di hay can doi lich.
            system_content += f"""

    THÔNG TIN THỜI TIẾT / KHÍ HẬU THỰC TIỄN:
    {weather_context}

    Khi tư vấn, hãy dùng phần này để nói rõ nên đi, nên cân nhắc, hoặc nên đổi lịch nếu rủi ro thời tiết cao."""

        if itinerary_text:
            system_content += f"""

    Dưới đây là LỊCH TRÌNH DU LỊCH TỐI ƯU đã được các thuật toán đồ thị (Dijkstra/Greedy) tính toán sẵn. Bạn hãy viết lời giới thiệu, tư vấn và mô tả chi tiết lịch trình này một cách tự nhiên, thân thiện và chi tiết bằng tiếng Việt. KHÔNG tự ý thay đổi thứ tự các địa điểm hoặc thời gian đã được định sẵn:
    {itinerary_text}"""

        system_content += f"""

    Ngữ cảnh thông tin chi tiết các địa điểm:
    {context}

    LƯU Ý: Bạn tuyệt đối KHÔNG được tự tạo ra khối JSON ở cuối câu trả lời. Hệ thống backend sẽ tự động đính kèm khối JSON lịch trình này ở cuối cùng sau khi bạn hoàn thành phản hồi."""

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

        # Helper cho Query Router

    def _build_fast_reply(self, route_decision) -> str:
        return (
            route_decision.reply or "Hệ thống hiện chỉ hỗ trợ tư vấn du lịch Việt Nam."
        )

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

        # [0] Route ques trước khi run full pipeline
        route_decision = await self.query_router.route(question, history)
        if route_decision.action == "fast_reply":
            answer = self._build_fast_reply(route_decision)
            print(f"\n[Query Router] Fast reply ({route_decision.intent}):{answer}")
            return answer

        # [1] Rewrite nếu có history
        search_question = await self._rewrite_question(question, history)

        # [2] Retrieve + Rerank + Recommend + Plan
        orch_res = await self.orchestrator.run(search_question)
        relevant_places = orch_res["places"]
        trip_request = orch_res["trip_request"]
        trip_plan = orch_res["trip_plan"]
        weather = orch_res.get("weather")

        # [3] Build context từ các relevant docs
        context = "\n\n".join(
            place.description for place in relevant_places if place.description
        )

        itinerary_text = None
        if trip_plan and trip_plan.days:
            itinerary_text = self._format_itinerary_for_llm(trip_plan)

        # Format weather rieng de prompt co du lieu thuc tien truoc khi LLM sinh cau tra loi.
        weather_context = self._format_weather_for_llm(weather)

        # [4] Build messages (system + history + question + itinerary_text + weather_context)
        messages = self._build_messages(
            history,
            context,
            question,
            itinerary_text,
            weather_context,
        )

        # [5] LLM generate
        try:
            result = await self.llm.ainvoke(messages)
            answer = result.content
        except (TimeoutError, asyncio.TimeoutError) as exc:
            print(
                f"[RAGInference] LLM response failed: {type(exc).__name__}: {exc}",
                flush=True,
            )
            answer = (
                "Xin lỗi, mô hình phản hồi đang bị timeout. "
                "Hệ thống vẫn đã xử lý truy vấn, vui lòng thử lại sau ít phút."
            )

        # Luôn đính kèm trip plan để frontend tạo Text/Timeline/Mindmap.
        serialized_plan = self.orchestrator._trip_plan_to_dict(trip_plan)
        json_block = f"\n\n```json\n{json.dumps(serialized_plan, ensure_ascii=False, indent=2)}\n```"
        answer += json_block

        print(f"\n [{self.model_info_core}]: {answer}")

        # [6] Lưu vào history
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
        history = self._get_history(session_id)  # session_id = conversation.id from DB

        # [0] Route ques trước khi run full pipeline
        route_decision = await self.query_router.route(question, history)
        if route_decision.action == "fast_reply":
            full_answer = self._build_fast_reply(route_decision)
            print(
                f"\n[Query Router] Fast stream reply ({route_decision.intent}):{full_answer}"
            )
            yield full_answer
            self._save_turn(session_id, question, full_answer)
            return

        # [1] Rewrite nếu có history
        search_question = await self._rewrite_question(question, history)

        # [2] Retrieve + Rerank + Recommend + Plan
        orch_res = await self.orchestrator.run(search_question)
        relevant_places = orch_res["places"]
        trip_request = orch_res["trip_request"]
        trip_plan = orch_res["trip_plan"]
        weather = orch_res.get("weather")

        # [3] Build context từ các relevant docs
        context = "\n\n".join(
            place.description for place in relevant_places if place.description
        )

        itinerary_text = None
        if trip_plan and trip_plan.days:
            itinerary_text = self._format_itinerary_for_llm(trip_plan)

        # Format weather rieng de prompt co du lieu thuc tien truoc khi LLM stream cau tra loi.
        weather_context = self._format_weather_for_llm(weather)

        # [4] Build messages (system + history + question + itinerary_text + weather_context)
        messages = self._build_messages(
            history,
            context,
            question,
            itinerary_text,
            weather_context,
        )

        # [5] LLM generate - STREAMING RESPONSE
        full_answer = ""
        try:
            async for chunk in self.llm.astream(messages):
                token = getattr(chunk, "content", "")
                if token:
                    full_answer += token
                    yield token
        except (TimeoutError, asyncio.TimeoutError) as exc:
            print(
                f"[RAGInference] LLM stream failed: {type(exc).__name__}: {exc}",
                flush=True,
            )
            fallback_answer = (
                "\n\nXin lỗi, mô hình phản hồi đang bị timeout. "
                "Hệ thống vẫn đã xử lý truy vấn, vui lòng thử lại sau ít phút."
            )
            full_answer += fallback_answer
            yield fallback_answer

        # Luôn đính kèm trip plan để frontend tạo Text/Timeline/Mindmap.
        serialized_plan = self.orchestrator._trip_plan_to_dict(trip_plan)
        json_block = f"\n\n```json\n{json.dumps(serialized_plan, ensure_ascii=False, indent=2)}\n```"
        full_answer += json_block
        yield json_block

        print(f"\n [{self.model_info_core}]: {full_answer}")

        # [6] Lưu vào history
        self._save_turn(session_id, question, full_answer)

    # Xóa lịch sử - API
    def clear_history(self, session_id: str = "default") -> None:
        """Xóa lịch sử của một session (dùng cho nút 'New Chat')."""
        self._history.pop(session_id, None)
        print(f"🗑️  History cleared for session: {session_id}")

    #
    def get_history_length(self, session_id: str = "default") -> int:
        """Trả về số lượt hội thoại (turns) của session."""
        return len(self._history[session_id]) // 2
