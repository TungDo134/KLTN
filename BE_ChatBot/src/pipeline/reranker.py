"""
pipeline/reranker.py
Reranker: lọc & sắp xếp lại top-K documents từ ChromaDB trước khi vào Recommender.

Mục đích:
  ChromaDB trả về top-20 theo cosine similarity (rag_score).
  Reranker tinh chỉnh lại thứ tự dựa trên nhiều tín hiệu hơn:
    - rag_score (embedding similarity)
    - rating của địa điểm
    - budget filter (loại bỏ nếu vượt ngân sách)
    - tag overlap bonus

Kết quả: top-K Place với rerank_score đã được tính.
"""
from src.core.schemas import Place, TripRequest


class Reranker:

    def __init__(self, top_k: int = 15):
        self.top_k = top_k

    def rerank(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Pseudo:
          # Bước 1: Filter cứng (hard filter)
          candidates = _hard_filter(places, request)

          # Bước 2: Tính rerank_score tổng hợp
          for p in candidates:
            tag_overlap = len(set(p.tags) & set(request.tags)) / max(len(request.tags), 1)
            p.rerank_score = (
                RAG_WEIGHT    * p.rag_score    +
                RATING_WEIGHT * (p.rating / 5) +
                TAG_WEIGHT    * tag_overlap
            )

          # Bước 3: Sort & slice top_k
          return sorted(candidates, key=lambda p: p.rerank_score, desc=True)[:top_k]
        """
        # TODO: implement
        pass

    def _hard_filter(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Loại bỏ những place không hợp lệ.
        Pseudo:
          filtered = []
          for p in places:
            # Chỉ giữ place thuộc đúng region (nếu region khớp)
            if request.region.lower() not in p.region.lower():
              continue
            # (Tương lai) lọc theo budget, giờ mở cửa, v.v.
            filtered.append(p)
          return filtered
        """
        # TODO: implement
        pass
