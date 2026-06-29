"""
recommend/content_based.py
Content-Based Filtering: so sánh tags của Place với tags trong TripRequest.

Thuật toán gợi ý:
  - Tính Jaccard similarity (hoặc TF-IDF cosine) giữa tags của place và tags của request
  - Cộng thêm bonus nếu rating cao
  - Kết quả gán vào place.recommend_score

Ví dụ:
  request.tags = ["cafe", "thác nước"]
  place.tags   = ["cafe", "check-in", "view"]
  → overlap = {"cafe"} → jaccard = 1/4 = 0.25
"""
from src.schemas import Place, TripRequest
from src.recommend.base_recommender import BaseRecommender


class ContentBasedRecommender(BaseRecommender):

    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Pseudo:
          for each place in places:
            overlap    = set(place.tags) ∩ set(request.tags)
            union      = set(place.tags) ∪ set(request.tags)
            jaccard    = len(overlap) / len(union)  if union else 0
            rating_bonus = (place.rating / 5.0) * RATING_WEIGHT
            place.recommend_score = jaccard + rating_bonus

          return sorted(places, key=lambda p: p.recommend_score, desc=True)
        """
        # TODO: implement
        pass

    def _jaccard_similarity(self, tags_a: list[str], tags_b: list[str]) -> float:
        """
        Pseudo:
          set_a = set(tags_a)
          set_b = set(tags_b)
          intersection = set_a & set_b
          union = set_a | set_b
          return len(intersection) / len(union) if union else 0.0
        """
        # TODO: implement
        pass
