"""
recommend/hybrid_recommender.py
Hybrid Recommender: chạy Content-Based + Location-Based tuần tự,
mỗi strategy cộng dồn recommend_score với trọng số riêng.

Trọng số mặc định (có thể cấu hình qua .env hoặc constructor):
  CONTENT_WEIGHT  = 0.6
  LOCATION_WEIGHT = 0.4
"""
from src.core.schemas import Place, TripRequest, RecommendResult
from src.recommend.content_based import ContentBasedRecommender
from src.recommend.location_based import LocationBasedRecommender
from src.recommend.base_recommender import BaseRecommender


class HybridRecommender(BaseRecommender):

    def __init__(self, top_k: int = 10, content_weight: float = 0.6, location_weight: float = 0.4):
        self.top_k = top_k
        self.content_weight = content_weight
        self.location_weight = location_weight
        self.content_rec = ContentBasedRecommender()
        self.location_rec = LocationBasedRecommender()

    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Pseudo:
          # Reset scores
          for p in places: p.recommend_score = 0.0

          # Chạy từng strategy, cộng dồn có trọng số
          places = content_rec.score(places, request)   → cộng content_weight * jaccard_score
          places = location_rec.score(places, request)  → cộng location_weight * proximity_score

          return sorted(places, key=lambda p: p.recommend_score, desc=True)
        """
        # TODO: implement
        pass

    def recommend(self, places: list[Place], request: TripRequest) -> RecommendResult:
        """
        Entry point chính.
        Pseudo:
          scored_places = self.score(places, request)
          top_places    = self.filter_top_k(scored_places, self.top_k)
          return RecommendResult(places=top_places, trip_request=request)
        """
        # TODO: implement
        pass
