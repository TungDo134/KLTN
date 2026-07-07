"""
pipeline/reranker.py
Reranker - metadata-based:: Loc ve su phu hop voi chuyen di (sau khi document rerank)

Mục đích:
  DocumentReranker trong rag_pipeline tra ve top_k
  Reranker tinh chinh lai thu tu dua tren nhieu tin hieu hon:
    - rag_score (embedding similarity)
    - rating của địa điểm
    - budget filter (loại bỏ nếu vượt ngân sách)
    - tag overlap bonus

Kết quả: top-K Place với rerank_score đã được tính.

Flow:
    places
        ↓
    _hard_filter()
        ↓
    candidates
        ↓
    _rank_score()
    _tag_overlap_score()
    _rating_score()
    _budget_score()
        ↓
    place.rerank_score
        ↓
    sort desc
        ↓
    top_k places
"""

from src.schemas import Place, TripRequest

# ============================================================
#                           CONSTANTS
# ============================================================
"""
- Độ tin tối thiểu của rating
- Dù ít review, ta vẫn tin rating ở mức tối thiểu 70%, không phạt quá nặng
"""
MIN_REVIEW_CONFIDENCE = 0.7

"""
- Thưởng tối đa do review_count đem lại
- Số lượng review chỉ có quyền cộng thêm tối đa 30% độ tin cậy còn lại
"""
REVIEW_CONFIDENCE_WEIGHT = 0.3

"""
- Ngưỡng review đủ tin cậy vì nếu một place có hơn 1000 review
- => Không cần được thưởng thêm
"""
REVIEW_COUNT_SATURATION = 1000

"""
- Giả định 1 ngày đi 3 địa điểm
- Lý do cần hệ số này: 
    - request.budget là ngân sách tổng chuyến đi, còn place.entrance_fee là phí của một địa điểm
    - Muốn so sánh tương đối, phải quy budget tổng về budget ước lượng cho mỗi địa điểm
"""
ESTIMATED_PLACES_PER_DAY = 3


class Reranker:
    def __init__(self, top_k: int = 10):
        self.top_k = top_k

    def rerank(self, places: list[Place], request: TripRequest) -> list[Place]:
        candidates = self._hard_filter(places, request)

        total = len(candidates)

        for index, place in enumerate(candidates):
            rank_score = self._rank_score(index, total)
            tag_score = self._tag_overlap_score(place, request)
            rating_score = self._rating_score(place)
            budget_score = self._budget_score(place, request)

            # Đưa về khoảng giá trị 0<x<1
            place.rerank_score = (
                rank_score + tag_score + rating_score + budget_score
            ) / 4

        return sorted(
            candidates,
            key=lambda place: place.rerank_score,
            reverse=True,
        )[: self.top_k]

    def _hard_filter(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        - Loại bỏ những place không hợp lệ.
        - Ver hiện tại chỉ đang filter theo **region**
        """
        region_filtered = []

        if not places:
            return []

        candidates = places

        if request.region:
            request_region = request.region.strip().lower()
            region_filtered = [
                place
                for place in candidates
                if request_region in place.region.strip().lower()
            ]

        if region_filtered:
            candidates = region_filtered

        return candidates

    def _rank_score(self, index: int, total: int):
        """
        Ý tưởng:
            - Tinh diem (trong so) vi tri hien tai cua Place sau buoc sap xep cua DocumentReranker => thanh diem trong khoang [0,1]
            - Giu lai quyet dinh cua document reranker + tinh chinh xep hang dua tren domain suitable

        Công thức: `1 - (index / (total - 1))`

        Ví dụ:
            - Với total = 20:
            - index = 0  (Place đứng đầu)  -> 1.0
            - index = 19 (Place đứng cuối) -> 0.0
        """
        if total <= 1:
            return 1.0

        return 1.0 - (index / (total - 1))

    def _tag_overlap_score(self, place: Place, request: TripRequest) -> float:
        """
        Ý tưởng:
            - Tính điểm (trọng số) của độ trùng khớp giữa user tags request & data tags place
            - Tận dụng các tags của data đã được ingest vào db => giúp `bám sát` hơn vào `yêu cầu` của ng dùng

        Công thức: `Số tag request được match / Tổng số tag request`

        Ví dụ:
            - User req: 'Tôi muốn đi Đà Lạt 2 ngày, chill, cafe, budget 2 triệu'
            - Sau quá trình `extract`:
                - request.tags = ["chill", "cafe"]
                - place.tags   = ["chill", "đồ uống", "thư giãn", "view đẹp"]
                - Tag được **match** ở đây là "**chill**" => matched = {"chill"}
            - score = 1 / 2 = 0.5
        """
        request_tags = {tag.strip().lower() for tag in request.tags if tag.strip()}
        if not request_tags:
            return 0.0

        place_tags = {tag.strip().lower() for tag in place.tags if tag.strip()}
        matched_tags = place_tags & request_tags

        return len(matched_tags) / len(request_tags)

    # Tính điểm chất lượng của Place dựa trên rating, số lượng review và độ tin cậy rating
    def _rating_score(self, place: Place) -> float:
        """
        Ý tưởng:
            - Tính điểm (trọng số) giữa chất lượng & độ tinh cậy dựa trên:
            - rating - rating.count - rating_is_reliable (đã **mapping** lại thông qua hàm **load_json_places**).
            - Tận dụng rating_count & rating_is_reliable.
            - Ít review không bị loại <=> Nhiều review được ưu tiên hơn.

        Công thức:
          **score = base * confidence * (0.7 + 0.3 * review_bonus)**

          Trong đó:
            - base = rating / 5.0
            - confidence = 1.0 nếu rating_is_reliable=True, ngược lại 0.7
            - review_bonus = min(rating_count / 1000, 1.0), tham số 1.0 là giới hạn trên
            - => Nếu review vượt 1000, vẫn chỉ tính tối đa là 1.0


        Giải thích:
          - base đưa rating về khoảng 0.0 - 1.0.
          - confidence phạt nhẹ dữ liệu rating không đáng tin.
          - review_bonus tăng dần theo số review, tối đa ở 1000 reviews.
          - (0.7 + 0.3 * review_bonus) đảm bảo place ít review không bị phạt về 0,
            nhưng place nhiều review vẫn có lợi thế.

        Ví dụ:
          rating  = 5.0, rating_count = 1000, reliable = True:
            score = 1.0 * 1.0 * 1.0 = 1.0

          rating  = 5.0, rating_count=300, reliable=False:
            score = 1.0 * 0.7 * (0.7 + 0.3 * 0.3)
                  = 0.7 * 0.79 = 0.553
        """

        base = max(0.0, min(place.rating / 5.0, 1.0))
        confidence = 1.0 if place.rating_is_reliable else 0.7

        review_bonus = max(0.0, min(place.rating_count / REVIEW_COUNT_SATURATION, 1.0))

        review_confidence = (
            MIN_REVIEW_CONFIDENCE + REVIEW_CONFIDENCE_WEIGHT * review_bonus
        )

        return base * confidence * review_confidence

    # Tính mức độ phù hợp chi phí của Place với budget trong TripRequest
    def _budget_score(self, place: Place, request: TripRequest) -> float:
        """
        Ý tưởng:
            - Tính điểm độ phù hợp giữa **place.entrance_fee** & **request.budget**
            - Tận dụng **entrance_fee**
            - Các địa điểm đắt/rẻ được phân biệt trong ranking.

        Công thức:
          estimated_place_count = request.days * 3
          per_place_budget = request.budget / estimated_place_count

          Nếu entrance_fee <= per_place_budget:
            score = 1.0

          Nếu entrance_fee > per_place_budget:
            score = 1 - ((entrance_fee - per_place_budget) / per_place_budget)

          Sau đó clamp về khoảng 0.0 - 1.0.

        Giải thích:
          Giả định mỗi ngày đi khoảng 3 địa điểm. Với chuyến 2 ngày budget 2 triệu:
            estimated_place_count = 2 * 3 = 6
            per_place_budget = 2,000,000 / 6 = 333,333

          Place có entrance_fee 100,000 vẫn score 1.0.
          Place có entrance_fee 500,000 sẽ bị giảm điểm nhưng không bị loại cứng.
        """

        if request.budget is None or request.budget <= 0:
            return 1.0

        estimated_place_count = max(request.days * 3, 1)
        per_place_budget = request.budget / estimated_place_count

        if per_place_budget <= 0:
            return 1.0

        entrance_fee = max(place.entrance_fee, 0.0)
        if entrance_fee <= per_place_budget:
            return 1.0

        over_budget_ratio = (entrance_fee - per_place_budget) / per_place_budget
        return max(0.0, 1.0 - over_budget_ratio)
