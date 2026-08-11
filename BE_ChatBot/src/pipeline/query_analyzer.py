"""
pipeline/query_analyzer.py
Phân tích câu hỏi tự nhiên của user → TripRequest có cấu trúc.

Sử dụng LLM (Llama) để extract:
  - region   : địa điểm muốn đến
  - days     : số ngày
  - tags     : sở thích / loại hình du lịch
  - budget   : ngân sách (nếu có)

Output là JSON được parse thành TripRequest dataclass.
"""

import asyncio
import json
import re
import unicodedata
from src.schemas import TripRequest
from src.core.llm_container import get_model_info
from src.services.travel_timing_service import TravelTimingService


# Prompt yêu cầu LLM trả về JSON thuần
_EXTRACT_PROMPT_TEMPLATE = """
Bạn là AI phân tích yêu cầu du lịch. Hãy phân tích câu sau và trả về JSON THUẦN (không markdown):
{{
  "region": "<tên địa điểm>",
  "days": <số ngày, integer>,
  "tags": ["<tag1>", "<tag2>", ...],
  "budget": <số tiền VND hoặc null>,
  "start_date": "<YYYY-MM-DD hoặc null>"
}}

Câu hỏi: {query}
"""


class QueryAnalyzer:
    def __init__(self, llm):
        """
        llm: [nvidia / meta/llama-3.3-70b-instruct]
        """
        print("\n- LLM cho trích xuất User Query => Trip Request [Query Analyzer]\n")
        self.llm_query_analyzer = llm
        self.travel_timing_service = TravelTimingService()
        self.model_info_query_analyzer = get_model_info(self.llm_query_analyzer)
        provider, model = self.model_info_query_analyzer.split(" / ", 1)
        print(f"🔧 Provider : {provider}")
        print(f"🔧 Model    : {model}")

    async def extract(self, raw_query: str) -> TripRequest:
        """
        Expected:
          prompt   = _EXTRACT_PROMPT_TEMPLATE.format(query=raw_query)
          response = await llm.ainvoke(prompt)
          text     = response.content  # chuỗi JSON

          data = json.loads(text)
          return TripRequest(
            raw_query = raw_query,
            region    = data["region"],
            days      = int(data["days"]),
            tags      = data.get("tags", []),
            budget    = data.get("budget"),
            start_date= data.get("start_date"),
          )
        """
        prompt = _EXTRACT_PROMPT_TEMPLATE.format(query=raw_query)
        try:
            # response = await self.llm_query_analyzer.ainvoke(prompt)
            # text = getattr(response, "content", str(response))
            # data = self._parse_response(text)
            print("[QueryAnalyzer] Calling LLM extract...", flush=True)

            response = await asyncio.wait_for(
                self.llm_query_analyzer.ainvoke(prompt),
                timeout=20,
            )
            print("[QueryAnalyzer] LLM extract done", flush=True)
            text = getattr(response, "content", str(response))
            data = self._parse_response(text)

        except Exception as exc:
            print(
                f"[QueryAnalyzer] extract failed: {type(exc).__name__}: {exc}",
                flush=True,
            )
            data = self._fallback_extract(raw_query)
            print("[QueryAnalyzer] fallback extract:", data, flush=True)

        timing_data = self.travel_timing_service.extract_fields(raw_query)
        for field, value in timing_data.items():
            if value is not None:
                data[field] = value

        days = data.get("days", 1)
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 1

        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = []

        normalized_tags = []
        for tag in tags:
            tag = str(tag).strip().lower()
            if tag and tag not in normalized_tags:
                normalized_tags.append(tag)

        budget = data.get("budget")
        if budget in ("", "null", None):
            budget = None
        else:
            try:
                budget = float(budget)
            except (TypeError, ValueError):
                budget = None

        start_date = data.get("start_date")
        if start_date in ("", "null", None):
            start_date = None
        else:
            start_date = str(start_date).strip()

        return TripRequest(
            raw_query=raw_query,
            region=str(data.get("region") or "").strip(),
            days=max(days, 1),
            tags=normalized_tags,
            budget=budget,
            start_date=start_date,
            origin_region=data.get("origin_region"),
            transport_mode=data.get("transport_mode"),
            day1_start_time=data.get("day1_start_time"),
            time_intent=data.get("time_intent"),
            auto_select_start_time=bool(data.get("auto_select_start_time", False)),
            flight_departure_at=data.get("flight_departure_at"),
            airport_transfer_minutes=data.get("airport_transfer_minutes"),
            flight_duration_minutes=data.get("flight_duration_minutes"),
            destination_transfer_minutes=data.get("destination_transfer_minutes"),
        )

    def _fallback_extract(self, raw_query: str) -> dict:
        """
        Rule-based fallback khi LLM extract timeout/lỗi.
        Chỉ bắt các field rõ ràng để tránh trả về TripRequest rỗng.
        """
        normalized = self._normalize_text(raw_query)
        data = {}

        region_aliases = [
            ("da lat", "\u0110\u00e0 L\u1ea1t"),
            ("dalat", "\u0110\u00e0 L\u1ea1t"),
            ("da nang", "\u0110\u00e0 N\u1eb5ng"),
            ("hoi an", "H\u1ed9i An"),
            ("ha noi", "H\u00e0 N\u1ed9i"),
            ("hanoi", "H\u00e0 N\u1ed9i"),
            ("ho chi minh", "H\u1ed3 Ch\u00ed Minh"),
            ("sai gon", "H\u1ed3 Ch\u00ed Minh"),
            ("tphcm", "H\u1ed3 Ch\u00ed Minh"),
            ("nha trang", "Nha Trang"),
            ("vung tau", "V\u0169ng T\u00e0u"),
            ("hue", "Hu\u1ebf"),
            ("sapa", "Sa Pa"),
            ("sa pa", "Sa Pa"),
            ("phu quoc", "Ph\u00fa Qu\u1ed1c"),
        ]
        for alias, region in region_aliases:
            if alias in normalized:
                data["region"] = region
                break

        days_match = re.search(r"\b(\d+)\s*(ngay|day|days)\b", normalized)
        if days_match:
            data["days"] = int(days_match.group(1))

        date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", raw_query)
        if date_match:
            data["start_date"] = date_match.group(1)

        budget_match = re.search(
            r"\b(\d+(?:[\.,]\d+)?)\s*(trieu|tr|million)\b",
            normalized,
        )
        if budget_match:
            amount = float(budget_match.group(1).replace(",", "."))
            data["budget"] = amount * 1_000_000

        tag_aliases = [
            ("chill", "chill"),
            ("cafe", "cafe"),
            ("ca phe", "cafe"),
            ("nghi duong", "nghi duong"),
            ("bien", "bien"),
            ("nui", "nui"),
            ("am thuc", "am thuc"),
            ("lich su", "lich su"),
            ("van hoa", "van hoa"),
            ("song ao", "song ao"),
        ]
        tags = []
        for alias, tag in tag_aliases:
            if alias in normalized and tag not in tags:
                tags.append(tag)
        if tags:
            data["tags"] = tags

        return data

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = text.replace("\u0111", "d")
        return re.sub(r"\s+", " ", text).strip()

    def _parse_response(self, text: str) -> dict:
        """
        Expected:
          clean = text.strip().removeprefix("```json").removesuffix("```").strip()
          return json.loads(clean)
        """
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
            raise ValueError("LLM response does not contain a JSON object")

        data = json.loads(clean[start : end + 1])
        if not isinstance(data, dict):
            raise ValueError("LLM response JSON must be an object")
        return data
