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
        llm: instance ChatNVIDIA / ChatAnthropic (bất kỳ LangChain ChatModel)
        """
        self.llm = llm

    async def extract(self, raw_query: str) -> TripRequest:
        """
        Pseudo:
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
        # TODO: implement
        pass

    def _parse_response(self, text: str) -> dict:
        """
        Pseudo:
          clean = text.strip().removeprefix("```json").removesuffix("```").strip()
          return json.loads(clean)
        """
        # TODO: implement
        pass
