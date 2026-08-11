"""
pipeline/orchestrator.py
Master Orchestrator — kết nối toàn bộ pipeline từ đầu đến cuối.

TRAVEL PIPELINE:
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
  [5] recommendation mode → skip planner
      OR
      trip_planning mode → TripPlanner → TripPlan
      ↓
  Result dict → RAGInference for response generation
"""

from typing import Literal

from src.pipeline.query_analyzer import QueryAnalyzer
from src.pipeline.rag_pipline import RAGStorage
from src.pipeline.reranker import Reranker
from src.planning.planner import TripPlanner
from src.recommend.hybrid_recommender import HybridRecommender
from src.schemas import Place, RecommendResult, TripPlan, TripRequest
from src.services.travel_timing_service import (
    TimingClarificationError,
    TravelTimingService,
)
from src.services.weather_service import WeatherService


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

        # WeatherService lay du lieu thoi tiet runtime de bo sung ngu canh tu van thuc tien.
        self.weather_service = WeatherService()
        self.travel_timing_service = TravelTimingService()

        # retriever              → MultiQueryRetriever (hybrid search)
        self.llm = llm

        # document_reranker -> DocumentReranker
        rag = RAGStorage()
        self.retriever, self.document_reranker = rag.get_multi_query_retriever()

    async def run(
        self,
        raw_query: str,
        mode: Literal["recommendation", "trip_planning"] = "trip_planning",
        response_language: str = "vi",
    ) -> dict:
        """
        Chay pipeline du lich theo execution mode.

        - recommendation: analyze -> retrieve -> rerank -> recommend.
        - trip_planning: chay them planner sau recommendation.
        """
        if mode not in {"recommendation", "trip_planning"}:
            raise ValueError(f"Unsupported orchestrator mode: {mode}")

        # ============================================================
        #                      BƯỚC 1: PHÂN TÍCH CÂU
        # ============================================================
        print("=============== BẮT ĐẦU FLOW ORCHESTRATOR ===============")

        # Trích xuất (Query Analyzer) các field quan trọng từ request của user
        trip_request = await self.analyzer.extract(raw_query)
        print("\n[Query Analyzer] Trip Request:", trip_request)

        timing_service = getattr(self, "travel_timing_service", None)
        timing_requested = (
            mode == "trip_planning"
            and timing_service is not None
            and timing_service.is_timing_requested(trip_request)
        )
        if timing_requested:
            clarification = timing_service.clarification_reply(
                trip_request,
                response_language,
            )
            if clarification:
                return self._clarification_result(
                    trip_request,
                    mode,
                    clarification,
                )

        # Tư vấn thời tiết (max 16 ngày, >16 => tổng quan data trước đó)
        weather = None
        if trip_request.region:
            # WeatherAdvice duoc tao sau QueryAnalyzer vi can region/start_date/days da trich xuat.
            weather = await self.weather_service.get_advice(
                trip_request.region,
                trip_request.start_date,
                trip_request.days,
            )
            print("\n[Weather Service] Weather Advice:", weather)

        if timing_requested and trip_request.auto_select_start_time:
            trip_request.day1_start_time = self._select_day1_start_time(weather)
            trip_request.time_intent = "auto_select"

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
        #                BUOC 3A: RERANK TAI LIEU -> TOP_K
        # DocumentReranker co the dung local HuggingFace hoac Cohere API.
        # ============================================================

        print("\n========= Reranking tài liệu (Document Reranker) =========")
        reranked_docs = self.document_reranker.compress_documents(raw_docs, raw_query)
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
        trip_plan = None
        if mode == "trip_planning":
            trip_plan = self.planner.plan(recommend_result)
            if timing_requested:
                first_place = self._first_scheduled_place(trip_plan)
            else:
                first_place = None
            if first_place is not None:
                try:
                    trip_plan.timing_advice = timing_service.build_advice(
                        trip_request,
                        first_place,
                        response_language,
                    )
                except TimingClarificationError as exc:
                    return self._clarification_result(
                        trip_request,
                        mode,
                        str(exc),
                    )

        budget_places = recommended_places
        if trip_plan is not None:
            budget_places = [
                scheduled_place.place
                for day in trip_plan.days
                for scheduled_place in day.places
            ]
        budget_summary = self._build_budget_summary(
            budget_places,
            trip_request,
        )

        return {
            "places": recommended_places,
            "trip_request": trip_request,
            "trip_plan": trip_plan,
            "weather": weather,
            "budget_summary": budget_summary,
            "execution_mode": mode,
            "clarification_reply": None,
        }

    def _clarification_result(
        self,
        trip_request: TripRequest,
        mode: str,
        reply: str,
    ) -> dict:
        return {
            "places": [],
            "trip_request": trip_request,
            "trip_plan": None,
            "weather": None,
            "budget_summary": None,
            "execution_mode": mode,
            "clarification_reply": reply,
        }

    def _select_day1_start_time(self, weather) -> str:
        risk_level = getattr(weather, "risk_level", "")
        if risk_level == "high":
            return "09:00"
        if risk_level == "medium":
            return "07:30"
        return "08:00"

    # Tính giờ rời nơi xuất phát
    def _first_scheduled_place(self, trip_plan: TripPlan):
        if not trip_plan:
            return None
        for day in trip_plan.days:
            if day.places:
                return day.places[0].place
        return None

    def _docs_to_places(self, documents: list) -> list:
        """
        LangChain Document
            - Đọc page_content và metadata
            - Chuẩn hóa dữ liệu
            - Tạo Place

        Chuyen LangChain Document thanh Place de dung cho cac buoc sau.
        DocumentReranker tra ve Document goc, con metadata reranker,
        recommender va planner lam viec voi Place co cau truc.

        Mapping metadata quan trong:
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

    def _entrance_fee_to_dict(self, place: Place) -> dict:
        """Classify a positive fee as estimated and zero as unclassified."""
        entrance_fee = max(float(getattr(place, "entrance_fee", 0) or 0), 0.0)
        return {
            "entrance_fee": entrance_fee,
            "entrance_fee_status": (
                "estimated" if entrance_fee > 0 else "unclassified_zero"
            ),
        }

    def _build_budget_summary(
        self,
        places: list[Place],
        trip_request: TripRequest,
    ) -> dict | None:
        """Summarize known entrance fees without estimating total trip cost."""
        requested_budget = getattr(trip_request, "budget", None)
        if requested_budget is None or requested_budget <= 0:
            return None

        fee_details = [self._entrance_fee_to_dict(place) for place in places]
        estimated_total = sum(item["entrance_fee"] for item in fee_details)
        known_fee_place_count = sum(
            item["entrance_fee_status"] == "estimated" for item in fee_details
        )
        total_place_count = len(fee_details)
        unclassified_fee_place_count = total_place_count - known_fee_place_count

        if estimated_total > requested_budget:
            status = "estimated_over_budget"
        elif total_place_count == 0 or unclassified_fee_place_count > 0:
            status = "partial"
        else:
            status = "estimated_within_budget"

        return {
            "scope": "entrance_fee_only",
            "requested_budget": float(requested_budget),
            "estimated_entrance_fee_total": estimated_total,
            "known_fee_place_count": known_fee_place_count,
            "unclassified_fee_place_count": unclassified_fee_place_count,
            "total_place_count": total_place_count,
            "status": status,
        }

    def _place_recommendation_to_dict(
        self,
        place: Place,
        response_language: str = "vi",
    ) -> dict:
        """Serialize the evidence used to explain why a place was recommended."""
        language = "en" if response_language == "en" else "vi"
        reasons = []
        matched_preference_tags = getattr(
            place,
            "matched_preference_tags",
            [],
        )

        if matched_preference_tags:
            if language == "en":
                reasons.append("Matches the travel preferences in your request.")
            else:
                matched_tags = ", ".join(matched_preference_tags)
                reasons.append(f"Phù hợp với sở thích: {matched_tags}.")

        rating = getattr(place, "rating", 0)
        rating_count = getattr(place, "rating_count", 0)
        rating_is_reliable = getattr(place, "rating_is_reliable", False)
        if rating_is_reliable and rating > 0:
            if language == "en":
                rating_reason = f"Has a reliable rating of {rating:.1f}/5"
                if rating_count > 0:
                    rating_reason += f" from {rating_count:,} reviews"
            else:
                formatted_rating = f"{rating:.1f}".replace(".", ",")
                rating_reason = f"Có mức đánh giá đáng tin cậy {formatted_rating}/5"
                if rating_count > 0:
                    formatted_rating_count = f"{rating_count:,}".replace(",", ".")
                    rating_reason += f" từ {formatted_rating_count} lượt đánh giá"
            reasons.append(rating_reason + ".")

        distance = getattr(place, "distance_to_candidate_centroid_km", None)
        location_score = getattr(place, "location_recommend_score", 0)
        # Only describe proximity for the nearer half of the candidate-distance range.
        if distance is not None and location_score >= 0.5:
            if language == "en":
                reasons.append(
                    "Located about "
                    f"{distance:.1f} km from the candidate cluster center, "
                    "making it easier to combine with nearby places."
                )
            else:
                formatted_distance = f"{distance:.1f}".replace(".", ",")
                reasons.append(
                    f"Cách trung tâm thành phố khoảng {formatted_distance} km, "
                    "thuận tiện kết hợp với các địa điểm lân cận."
                )

        return {
            "name": getattr(place, "name", ""),
            "recommendation_reasons": reasons[:3],
        }

    def _trip_plan_to_dict(
        self,
        plan: TripPlan,
        response_language: str = "vi",
    ) -> dict:
        """
        Serialize TripPlan → dict để JSON response cho frontend.
        """
        best_time_map = {
            "đà lạt": "11-03",
            "đà nẵng": "02-08",
            "hà nội": "09-11 & 03-04",
            "ha noi": "09-11 & 03-04",
            "hanoi": "09-11 & 03-04",
            "hồ chí minh": "12-04",
            "nha trang": "01-09",
            "vũng tàu": "11-04",
        }
        region_lower = (plan.trip_request.region or "").strip().lower()
        best_time = best_time_map.get(region_lower, "11-04")
        language = "en" if response_language == "en" else "vi"
        region = plan.trip_request.region or ""
        days = plan.trip_request.days or 0
        scheduled_places = [
            scheduled_place.place for day in plan.days for scheduled_place in day.places
        ]
        budget_summary = self._build_budget_summary(
            scheduled_places,
            plan.trip_request,
        )

        if language == "en":
            title = f"Explore {region} in {days} days"
            day_title = f"Explore {region}"
            description_template = (
                "An optimized sightseeing route and schedule "
                "({place_count} {place_label})."
            )
        else:
            title = f"Hành trình khám phá {region} {days} ngày"
            day_title = f"Khám phá {region}"
            description_template = (
                "Hành trình tham quan tối ưu đường đi và thời gian "
                "({place_count} {place_label})."
            )

        return {
            "title": title,
            "region": plan.trip_request.region,
            "best_time": best_time,
            "language": language,
            "budget_summary": budget_summary,
            "timing_advice": (
                getattr(plan, "timing_advice", None).to_dict()
                if getattr(plan, "timing_advice", None) is not None
                else None
            ),
            "days": [
                {
                    "day": day.day,
                    "title": day_title,
                    "estimated_entrance_fee_total": sum(
                        self._entrance_fee_to_dict(sp.place)["entrance_fee"]
                        for sp in day.places
                    ),
                    "description": description_template.format(
                        place_count=len(day.places),
                        place_label=("place" if len(day.places) == 1 else "places")
                        if language == "en"
                        else "địa điểm",
                    ),
                    "places": [
                        {
                            **self._place_recommendation_to_dict(
                                sp.place,
                                language,
                            ),
                            **self._entrance_fee_to_dict(sp.place),
                            "arrival": sp.arrival_time,
                            "departure": sp.departure_time,
                            "tags": sp.place.tags if language == "vi" else [],
                        }
                        for sp in day.places
                    ],
                }
                for day in plan.days
            ],
        }
