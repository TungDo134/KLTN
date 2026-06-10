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

import json
from src.core.schemas import TripRequest
from src.core.llm_container import get_model_info


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
        print("\n- LLM cho trích xuất User Query => Trip Request [QueryAnalyzer]\n")
        self.llm_query_analyzer = llm
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
            response = await self.llm_query_analyzer.ainvoke(prompt)
            text = getattr(response, "content", str(response))
            data = self._parse_response(text)
        except Exception as exc:
            print("[QueryAnalyzer] extract failed:", exc)
            data = {}

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
        )

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
