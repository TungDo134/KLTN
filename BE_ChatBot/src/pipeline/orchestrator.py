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

from src.schemas import Place, TripRequest, TripPlan, RecommendResult
from src.pipeline.query_analyzer import QueryAnalyzer
from src.pipeline.rag_pipline import RAGStorage
from src.pipeline.reranker import Reranker
from src.recommend.hybrid_recommender import HybridRecommender
from src.planning.planner import TripPlanner


class TripOrchestrator:
    def __init__(
        self,
        llm,
        top_k_rerank: int = 20,
        top_k_rerank_metadata=15,
        top_k_recommend: int = 10,
    ):
        # Trích xuất ý định người dùng => tags
        self.analyzer = QueryAnalyzer(llm)

        # Re-rank lại dựa trên trực tiếp các metadata của dữ liệu
        self.reranker = Reranker(top_k=top_k_rerank_metadata)

        # Module Recommendation
        self.recommender = HybridRecommender(top_k=top_k_recommend)

        # Module Graph Planning
        self.planner = TripPlanner(route_algorithm="dijkstra")

        # retriever              → MultiQueryRetriever (hybrid search)
        self.llm = llm

        # cross_encoder_reranker → CrossEncoderReranker
        rag = RAGStorage()
        self.retriever, self.cross_encoder_reranker = rag.get_multi_query_retriever()

    async def run(self, raw_query: str) -> list[Place]:
        """
        Flow Pipeline

        User Request → Query Analyze → Retrieve → Hybrid Rerank (CrossEncoder + metadata-based)
                        ↓
        Recommend → Plan → Generate.
        """

        # ============================================================
        #                      BƯỚC 1: PHÂN TÍCH CÂU
        # ============================================================

        trip_request = await self.analyzer.extract(raw_query)
        print("\n[QueryAnalyzer] TripRequest:", trip_request)

        # ============================================================
        #               BƯỚC 2: MULTI-QUERY + HYBRID SEARCH
        #
        # MultiQueryRetriever: sinh N query variations → Hybrid Search (Vector + BM25) → dedup
        # ============================================================

        raw_docs = await self.retriever.ainvoke(raw_query)
        print(
            f"========= Tìm thấy {len(raw_docs)} tài liệu liên quan "
            f"(Multi-Query + Hybrid Search) ========="
        )

        # ============================================================
        #                BƯỚC 3A: RERANK(CROSS-ENCODER) -> TOP_K
        # CrossEncoder nhìn (query, doc) cùng lúc →  chính xác hơn embedding
        # ============================================================

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

        # ============================================================
        #        BƯỚC 3B: CONVERT -> PLACES -> RERANK (METADATA)
        # ============================================================
        places = self._docs_to_places(reranked_docs)
        print(f"\n [Doc to places] Converted {len(places)} places")

        for i, place in enumerate(places[:3], 1):
            print(f"\n[_docs_to_places] Place {i}")
            print(f"  name               : {place.name}")
            print(f"  place_type         : {place.place_type}")
            print(f"  region             : {place.region}")
            print(f"  entrance_fee       : {place.entrance_fee}")
            print(f"  rating             : {place.rating}")
            print(f"  rating_count       : {place.rating_count}")
            print(f"  rating_is_reliable : {place.rating_is_reliable}")
            print(f"  open_time          : {place.open_time}")
            print(f"  close_time         : {place.close_time}")

        reranked_places = self.reranker.rerank(places, trip_request)

        print(f"\n[Metadata Reranker] Reranked {len(reranked_places)} places")
        for i, place in enumerate(reranked_places[:5], 1):
            print(f"\n[Metadata Reranker] Place {i}")
            print(f"  name          : {place.name}")
            print(f"  region        : {place.region}")
            print(f"  tags          : {place.tags}")
            print(f"  rating        : {place.rating}")
            print(f"  entrance_fee  : {place.entrance_fee}")
            print(f"  rerank_score  : {place.rerank_score}")

        # ================================================================
        #        BƯỚC 4: RECOMMENDATION (HYBRID (CONTENT+LOCATION BASED))
        # ================================================================
        recommend_result = self.recommender.recommend(reranked_places, trip_request)
        recommended_places = recommend_result.places

        print(f"\n[Hybrid Recommender] Recommended {len(recommended_places)} places")
        for i, place in enumerate(recommended_places, 1):
            print(f"\n[Recommend] Place {i}")
            print(f"  name             : {place.name}")
            print(f"  region           : {place.region}")
            print(f"  tags             : {place.tags}")
            print(f"  rating           : {place.rating}")
            print(f"  rerank_score     : {place.rerank_score}")
            print(f"  recommend_score  : {place.recommend_score}")

        # ================================================================
        #        BƯỚC 5: PLANNING
        # ================================================================
        trip_plan = self.planner.plan(recommend_result)

        return {
            "places": recommended_places,
            "trip_request": trip_request,
            "trip_plan": trip_plan,
        }

    def _docs_to_places(self, documents: list) -> list:
        """
        Convert LangChain Document objects → Place dataclass.
        CrossEncoder returns documents, but the metadata reranker,
        recommender, and planner work with structured Place objects.
        This method maps the flat metadata created in rag_pipline.py into
        the Place schema and keeps doc.page_content as the place description.

        Important metadata mapping:
          - type -> Place.place_type
          - address -> Place.address
          - rating.score -> Place.rating
          - rating.count -> Place.rating_count
          - rating.is_reliable -> Place.rating_is_reliable
          - open -> Place.open_time
          - close -> Place.close_time
          - avg_duration_minutes -> Place.avg_duration_minutes
          - open + close -> Place.opening_hours
          - entrance_fee -> Place.entrance_fee
          - best_time -> Place.best_time
          - source_url -> Place.source_url
          - tags string from Chroma -> list[str]
        """
        places = []
        for doc in documents:
            meta = doc.metadata
            open_time = str(meta.get("open") or "").strip()
            close_time = str(meta.get("close") or "").strip()
            opening_hours = None
            if open_time or close_time:
                opening_hours = f"{open_time} - {close_time}".strip(" -")

            tags = meta.get("tags", "")
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            elif not isinstance(tags, list):
                tags = []

            places.append(
                Place(
                    place_id=str(meta.get("place_id") or meta.get("name") or "unknown"),
                    name=str(meta.get("name") or "Unknown"),
                    region=str(meta.get("region") or ""),
                    lat=float(meta.get("lat") or 0),
                    lng=float(meta.get("lng") or 0),
                    tags=tags,
                    rating=float(meta.get("rating_score") or 0),
                    avg_duration_minutes=int(meta.get("avg_duration_minutes") or 60),
                    opening_hours=opening_hours,
                    description=doc.page_content,
                    place_type=str(meta.get("type") or ""),
                    address=meta.get("address") or None,
                    rating_count=int(meta.get("rating_count") or 0),
                    rating_is_reliable=bool(meta.get("rating_is_reliable") or False),
                    open_time=open_time or None,
                    close_time=close_time or None,
                    entrance_fee=float(meta.get("entrance_fee") or 0),
                    best_time=meta.get("best_time") or None,
                    source_url=meta.get("source_url") or None,
                    rag_score=float(meta.get("score") or 0),
                )
            )

        return places

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
        """
        best_time_map = {
            "đà lạt": "11-03",
            "đà nẵng": "02-08",
            "hà nội": "09-11 & 03-04",
            "hồ chí minh": "12-04",
            "nha trang": "01-09",
            "vũng tàu": "11-04"
        }
        region_lower = (plan.trip_request.region or "").strip().lower()
        best_time = best_time_map.get(region_lower, "11-04")

        return {
            "title": f"Hành trình khám phá {plan.trip_request.region or ''} {plan.trip_request.days or 0} Ngày",
            "region": plan.trip_request.region,
            "best_time": best_time,
            "days": [
                {
                    "day": day.day,
                    "title": f"Ngày {day.day}: Khám phá {plan.trip_request.region or ''}",
                    "description": f"Hành trình tham quan tối ưu đường đi và thời gian ({len(day.places)} địa điểm).",
                    "places": [
                        {
                            "name": sp.place.name,
                            "arrival": sp.arrival_time,
                            "departure": sp.departure_time,
                            "tags": sp.place.tags,
                        }
                        for sp in day.places
                    ]
                }
                for day in plan.days
            ]
        }
