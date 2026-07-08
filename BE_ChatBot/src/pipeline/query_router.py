import json
import re
import unicodedata
from dataclasses import dataclass


@dataclass
class RouteDecision:
    intent: str
    action: str
    confidence: float
    reply: str | None = None
    reason: str = ""


_SMALL_TALK_KEYWORDS = {
    "hi",
    "hello",
    "xin chao",
    "chao",
    "chao ban",
    "cam on",
    "thanks",
    "thank you",
    "tam biet",
    "bye",
}

_DESTINATION_KEYWORDS = {
    "da lat",
    "dalat",
    "da nang",
    "ha noi",
    "hcm",
    "sai gon",
    "ho chi minh",
    "nha trang",
    "vung tau",
    "hue",
    "hoi an",
    "sapa",
    "sa pa",
    "phu quoc",
}

_TRAVEL_KEYWORDS = {
    "du lich",
    "di choi",
    "tham quan",
    "lich trinh",
    "hanh trinh",
    "tour",
    "dia diem",
    "diem den",
    "goi y",
    "de xuat",
    "nen di dau",
    "an gi",
    "quan an",
    "khach san",
    "homestay",
    "di chuyen",
    "ve",
    "chi phi",
    "ngan sach",
    "thoi tiet",
    "mua gi",
    "mang gi",
}


class QueryRouter:
    def __init__(self, llm=None):
        self.llm = llm

    async def route(self, question: str, history: list | None = None) -> RouteDecision:
        history = history or []
        text = self._normalize(question)
        has_history = self._has_history(history)

        if not text or text in {"?", ".", "...", "!"}:
            return self._fast_reply(
                "small_talk",
                "Vui lòng nhập điểm đến hoặc nhu cầu du lịch cần tư vấn.",
                1.0,
                "Empty or too short query.",
            )

        if self._is_small_talk_only(text):
            return self._fast_reply(
                "small_talk",
                "Xin chào, hãy nhập điểm đến hoặc nhu cầu du lịch cần tư vấn.",
                1.0,
                "Small talk only.",
            )

        if self._has_travel_signal(text):
            return RouteDecision(
                intent="travel",
                action="run_pipeline",
                confidence=0.9,
                reason="Current query has explicit travel-domain signal.",
            )

        if has_history:
            if not self.llm:
                return self._fast_reply(
                    "not_travel",
                    "Hệ thống hiện chỉ hỗ trợ tư vấn du lịch Việt Nam.",
                    0.5,
                    "History exists but no LLM classifier is available.",
                )

            return await self._route_by_llm(question, history)

        return self._fast_reply(
            "not_travel",
            "Hệ thống hiện chỉ hỗ trợ tư vấn du lịch Việt Nam.",
            0.8,
            "No travel-domain signal and no history to disambiguate.",
        )

    async def _route_by_llm(self, question: str, history: list) -> RouteDecision:
        prompt = self._build_classifier_prompt(question, history)

        try:
            response = await self.llm.ainvoke(prompt)
            text = getattr(response, "content", str(response))
            data = self._parse_json(text)
        except Exception as exc:
            return self._fast_reply(
                "not_travel",
                "Hệ thống hiện chỉ hỗ trợ tư vấn du lịch Việt Nam.",
                0.5,
                f"LLM classifier failed: {type(exc).__name__}",
            )

        intent = str(data.get("intent") or "not_travel").strip()
        try:
            confidence = float(data.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5

        if intent in {"travel", "travel_follow_up"} and confidence >= 0.6:
            return RouteDecision(
                intent=intent,
                action="run_pipeline",
                confidence=confidence,
                reason="LLM classifier confirmed travel-domain context.",
            )

        return self._fast_reply(
            "not_travel",
            "Hệ thống hiện chỉ hỗ trợ tư vấn du lịch Việt Nam.",
            confidence,
            "LLM classifier did not confirm travel-domain context.",
        )

    def _build_classifier_prompt(self, question: str, history: list) -> str:
        history_text = self._history_to_text(history[-6:])
        return f"""
You are a strict domain classifier for a Vietnam travel advisory chatbot.

Rule:
- Run the pipeline ONLY if the current question is about travel in Vietnam,
  or if it is a follow-up to a previous Vietnam travel conversation.
- If the question is not clearly travel-related, classify it as "not_travel".
- Do not answer the user.
- Return pure JSON only, no markdown.

Valid intents:
- "travel": the current question itself is clearly about travel.
- "travel_follow_up": the current question is ambiguous alone, but history proves it continues a travel conversation.
- "not_travel": the current question is not travel-related, or history is not enough to prove travel context.

Recent history:
{history_text}

Current question:
{question}

JSON:
{{
  "intent": "travel | travel_follow_up | not_travel",
  "confidence": 0.0
}}
""".strip()

    def _has_travel_signal(self, text: str) -> bool:
        return self._contains_any(text, _DESTINATION_KEYWORDS) or self._contains_any(
            text, _TRAVEL_KEYWORDS
        )

    def _is_small_talk_only(self, text: str) -> bool:
        cleaned = re.sub(r"[^\w\s]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if len(cleaned) > 40:
            return False

        return self._contains_any(cleaned, _SMALL_TALK_KEYWORDS)

    def _has_history(self, history: list) -> bool:
        return bool(self._history_to_text(history).strip())

    def _contains_any(self, text: str, keywords: set[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _history_to_text(self, history: list) -> str:
        parts = []
        for message in history:
            content = str(getattr(message, "content", "")).strip()
            if content:
                parts.append(content[:500])
        return "\n".join(parts)

    def _fast_reply(
        self,
        intent: str,
        reply: str,
        confidence: float,
        reason: str,
    ) -> RouteDecision:
        return RouteDecision(
            intent=intent,
            action="fast_reply",
            confidence=confidence,
            reply=reply,
            reason=reason,
        )

    def _normalize(self, text: str) -> str:
        text = str(text or "").lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = text.replace("đ", "d").replace("Ä‘", "d")
        return re.sub(r"\s+", " ", text).strip()

    def _parse_json(self, text: str) -> dict:
        clean = text.strip()

        if clean.startswith("```"):
            lines = clean.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean = "\n".join(lines).strip()

        start = clean.find("{")
        end = clean.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("Classifier response does not contain JSON object")

        data = json.loads(clean[start : end + 1])
        if not isinstance(data, dict):
            raise ValueError("Classifier JSON must be an object")
        return data
