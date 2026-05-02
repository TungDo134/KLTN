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
from src.pipeline.rag_pipline import RAGStorage
from src.pipeline.reranker import Reranker
from src.recommend.hybrid_recommender import HybridRecommender
from src.planning.planner import TripPlanner


class TripOrchestrator:
    def __init__(self, llm, top_k_rerank: int = 15, top_k_recommend: int = 10):
        self.analyzer = QueryAnalyzer(llm)
        self.reranker = Reranker(top_k=top_k_recommend)  # metadata-based, top-10
        self.recommender = HybridRecommender(top_k=top_k_recommend)
        self.planner = TripPlanner()

        self.llm = llm
        # retriever              → MultiQueryRetriever (hybrid search, ~30 unique docs)
        # cross_encoder_reranker → CrossEncoderReranker (top-15 hiện tại)
        rag = RAGStorage()
        self.retriever, self.cross_encoder_reranker = rag.get_multi_query_retriever()

    async def run(self, raw_query: str) -> dict:
        """
        Flow Pipeline

        Query → Analyze → Retrieve → Hybrid Rerank (CrossEncoder + metadata-based)
                        ↓
        Recommend → Plan → Generate.
        """

        # =========  Bước 1: Phân tích câu hỏi =========
        trip_request = await self.analyzer.extract(raw_query)

        # =========  Bước 2: Multi-Query + Hybrid Search → ~30 unique docs =========
        # MultiQueryRetriever: sinh N query variations → Hybrid Search (Vector + BM25) → dedup
        raw_docs = await self.retriever.ainvoke(raw_query)
        print(
            f"========= Tìm thấy {len(raw_docs)} tài liệu liên quan "
            f"(Multi-Query + Hybrid Search) ========="
        )

        # =========  Bước 3a: CrossEncoder rerank → top-N docs (ngữ nghĩa) =========
        # CrossEncoder nhìn (query, doc) cùng lúc →  chính xác hơn embedding
        print("\n========= Reranking tài liệu (CrossEncoder) =========")
        reranked_docs = self.cross_encoder_reranker.compress_documents(
            raw_docs, raw_query
        )
        print(f"\n========= Sau Rerank: {len(reranked_docs)} tài liệu =========")

        for i, doc in enumerate(reranked_docs, 1):
            clean_text = doc.page_content.replace("\r", "").replace("\n", " ")
            clean_text = " ".join(clean_text.split())
            preview = clean_text[:150]
            print(f"\n 📄 Doc {i}: {preview}...")

        return reranked_docs

        # ============================================================ #
        # LATER
        # ============================================================ #

        # =========  Bước 3b: Convert → Places rồi metadata rerank → top-10 =========
        # places = self._docs_to_places(reranked_docs)
        # reranked_places = self.reranker.rerank(places, trip_request)

        # # =========  Bước 4: Recommend =========
        # recommend_result = self.recommender.recommend(reranked_places, trip_request)

        # # =========  Bước 5: Planning =========
        # trip_plan = self.planner.plan(recommend_result)

        # # ── Bước 6: Generation =========
        # response_text = await self._generate_response(trip_request, trip_plan)

        # return {
        #     "text": response_text,
        #     "trip_plan": self._trip_plan_to_dict(trip_plan),
        # }

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
