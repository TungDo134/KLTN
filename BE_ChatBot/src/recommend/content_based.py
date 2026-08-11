"""
recommend/content_based.py
Content-Based Filtering: so sánh/chọn địa điểm có tags của Place với tags trong TripRequest.

Thuật toán gợi ý:
  - Tính Jaccard similarity (độ giống giữa 2 tags) tags của place và tags của request
  - Cộng thêm bonus nếu rating cao
  - Kết quả gán vào place.recommend_score

Ví dụ:
  request.tags = ["cafe", "thác nước"]
  place.tags   = ["cafe", "check-in", "view"]
  → overlap = {"cafe"} → jaccard = 1/4 = 0.25
"""

from src.recommend.base_recommender import BaseRecommender
from src.schemas import Place, TripRequest

"""CONSTANT"""
RATING_WEIGHT = 0.2


class ContentBasedRecommender(BaseRecommender):
    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        """Tinh `raw content score` = `Jaccard tag similar + rating bonus`"""
        for place in places:
            place.matched_preference_tags = self._matched_tags(
                place.tags,
                request.tags,
            )
            jaccard = self._jaccard_similarity(place.tags, request.tags)
            rating_bouns = (place.rating / 5.0) * RATING_WEIGHT
            place.recommend_score = jaccard + rating_bouns
        return sorted(places, key=lambda place: place.recommend_score, reverse=True)

    def _matched_tags(
        self,
        place_tags: list[str],
        request_tags: list[str],
    ) -> list[str]:
        """Tra ve cac tag trong request khop chinh xac voi tag cua dia diem."""
        normalized_place_tags = {
            tag.strip().lower() for tag in place_tags if tag.strip()
        }
        matched_tags = []
        for tag in request_tags:
            normalized_tag = tag.strip().lower()
            if (
                normalized_tag in normalized_place_tags
                and normalized_tag not in matched_tags
            ):
                matched_tags.append(normalized_tag)
        return matched_tags

    def _jaccard_similarity(self, tags_a: list[str], tags_b: list[str]) -> float:
        """
        - Tinh `Jaccard Similarity` sau khi normalize lowercase + strip
        - VD:
            - Request = {cafe, ẩm thực}
            - Place   = {cafe, check-in, view}

            - Tag chung = {cafe}                             → 1
            - Tất cả tag = {cafe, ẩm thực, check-in, view}   → 4
        | `=> Jaccard = 1 / 4 = 0.25` càng cao => địa điểm càng khớp với sở thích
        """
        set_a = {tag.strip().lower() for tag in tags_a if tag.strip()}
        set_b = {tag.strip().lower() for tag in tags_b if tag.strip()}

        union = set_a | set_b
        if not union:
            return 0.0

        intersection = set_a & set_b

        return len(intersection) / len(union)
