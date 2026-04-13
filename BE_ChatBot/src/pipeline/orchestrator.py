"""
pipeline/orchestrator.py
Master Orchestrator — kết nối toàn bộ pipeline từ đầu đến cuối.

FULL FLOW:
  raw_query (str)
      ↓
  [1] QueryAnalyzer     → TripRequest
      ↓
  [2] RAGStorage        → top-20 Place (ChromaDB similarity search)
      ↓
  [3] Reranker          → top-15 Place (multi-signal reranking)
      ↓
  [4] HybridRecommender → top-10 Place (content + location scoring)
      ↓
  [5] TripPlanner       → TripPlan (graph + route + schedule)
      ↓
  [6] LLM Generation    → natural language response + structured JSON
      ↓
  Response (dict)  →  FastAPI / Gradio
"""
from src.core.schemas import TripRequest, TripPlan
from src.pipeline.query_analyzer import QueryAnalyzer
from src.pipeline.reranker import Reranker
from src.recommend.hybrid_recommender import HybridRecommender
from src.planning.planner import TripPlanner


class TripOrchestrator:

    def __init__(self, llm, retriever, top_k_rerank: int = 15, top_k_recommend: int = 10):
        self.llm         = llm
        self.retriever   = retriever
        self.analyzer    = QueryAnalyzer(llm)
        self.reranker    = Reranker(top_k=top_k_rerank)
        self.recommender = HybridRecommender(top_k=top_k_recommend)
        self.planner     = TripPlanner()

    async def run(self, raw_query: str) -> dict:
        """
        Pseudo:

        # ── Bước 1: Phân tích câu hỏi ──────────────────────────────
        trip_request = await analyzer.extract(raw_query)

        # ── Bước 2: RAG — ChromaDB search ──────────────────────────
        raw_docs = await retriever.ainvoke(raw_query)
        places   = _docs_to_places(raw_docs)   # convert Document → Place

        # ── Bước 3: Rerank ─────────────────────────────────────────
        reranked_places = reranker.rerank(places, trip_request)

        # ── Bước 4: Recommend ──────────────────────────────────────
        recommend_result = recommender.recommend(reranked_places, trip_request)

        # ── Bước 5: Planning ───────────────────────────────────────
        trip_plan = planner.plan(recommend_result)

        # ── Bước 6: Generation ─────────────────────────────────────
        response_text = await _generate_response(trip_request, trip_plan)

        return {
            "text"      : response_text,
            "trip_plan" : _trip_plan_to_dict(trip_plan),  # JSON cho FE timeline/mindmap
        }
        """
        # TODO: implement
        pass

    def _docs_to_places(self, documents: list) -> list:
        """
        Convert LangChain Document objects → Place dataclass.
        Pseudo:
          places = []
          for doc in documents:
            meta = doc.metadata
            places.append(Place(
              place_id = meta.get("place_id", str(uuid4())),
              name     = meta.get("name", "Unknown"),
              region   = meta.get("region", ""),
              lat      = float(meta.get("lat", 0)),
              lon      = float(meta.get("lon", 0)),
              tags     = meta.get("tags", "").split(","),
              rating   = float(meta.get("rating", 3.0)),
              avg_duration_minutes = int(meta.get("duration", 60)),
              opening_hours = meta.get("opening_hours"),
              description   = doc.page_content,
              rag_score     = meta.get("score", 0.0),
            ))
          return places
        """
        # TODO: implement
        pass

    async def _generate_response(self, request: TripRequest, plan: TripPlan) -> str:
        """
        Dùng LLM tạo văn bản phản hồi tự nhiên từ TripPlan.
        Pseudo:
          prompt = _build_generation_prompt(request, plan)
          response = await llm.ainvoke(prompt)
          return response.content
        """
        # TODO: implement
        pass

    def _build_generation_prompt(self, request: TripRequest, plan: TripPlan) -> str:
        """
        Tạo prompt cho LLM Generation.
        Pseudo:
          itinerary_text = format TripPlan thành dạng text (ngày, giờ, địa điểm)
          return f'''Bạn là trợ lý du lịch. Hãy trình bày lịch trình sau bằng tiếng Việt thân thiện:
          Chuyến đi: {request.region}, {request.days} ngày
          {itinerary_text}
          Hãy thêm mô tả ngắn cho mỗi địa điểm và lời khuyên hữu ích.'''
        """
        # TODO: implement
        pass

    def _trip_plan_to_dict(self, plan: TripPlan) -> dict:
        """
        Serialize TripPlan → dict để JSON response cho frontend.
        Pseudo:
          return {
            "days": [
              {
                "day": day.day,
                "places": [
                  {
                    "name": sp.place.name,
                    "arrival": sp.arrival_time,
                    "departure": sp.departure_time,
                    "lat": sp.place.lat,
                    "lon": sp.place.lon,
                    "tags": sp.place.tags,
                  }
                  for sp in day.places
                ]
              }
              for day in plan.days
            ]
          }
        """
        # TODO: implement
        pass
