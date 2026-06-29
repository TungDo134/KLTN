"""
recommend/hybrid_recommender.py
Hybrid Recommender: chạy Content-Based + Location-Based tuần tự,
mỗi strategy cộng dồn recommend_score với trọng số riêng.

Trọng số mặc định (có thể cấu hình qua .env hoặc constructor):
  CONTENT_WEIGHT  = 0.6
  LOCATION_WEIGHT = 0.4
"""

from src.schemas import Place, TripRequest, RecommendResult
from src.recommend.content_based import ContentBasedRecommender
from src.recommend.location_based import LocationBasedRecommender
from src.recommend.base_recommender import BaseRecommender


class HybridRecommender(BaseRecommender):
    def __init__(
        self, top_k: int = 10, content_weight: float = 0.6, location_weight: float = 0.4
    ):
        self.top_k = top_k
        self.content_weight = content_weight
        self.location_weight = location_weight
        self.content_rcm = ContentBasedRecommender()
        self.location_rcm = LocationBasedRecommender()

    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Ket hop `raw (content score + location score) = weighted sum`
        """
        if not places:
            return places
        for place in places:
            place.recommend_score = 0.0

        places = self.content_rcm.score(places, request)
        content_scores = {id(place): place.recommend_score for place in places}

        for place in places:
            place.recommend_score = 0.0

        places = self.location_rcm.score(places, request)

        for place in places:
            place.recommend_score = (
                content_scores[id(place)] * self.content_weight
                + place.recommend_score * self.location_weight
            )

        return sorted(
            places,
            key=lambda place: place.recommend_score,
            reverse=True,
        )

    def recommend(self, places: list[Place], request: TripRequest) -> RecommendResult:
        """
        Entry point chinh: score, lay top-k, wrap thanh RecommendResult.
        """
        scored_places = self.score(places, request)
        top_places = self.filter_top_k(scored_places, self.top_k)
        return RecommendResult(places=top_places, trip_request=request)
