# ============================================================
# PURE FUNCTIONS — không phụ thuộc bất kỳ external lib nào
# Không bao giờ cần sửa file này
# ============================================================

import math
from typing import List, Dict, Set


def precision_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """
    Tỉ lệ docs relevant trong top-K kết quả.

    Ví dụ: retrieved = [A, B, C, D, E], relevant = {A, C, X}
    Precision@3 = 2/3 (A và C hit trong top-3)
    """
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / k


# def dcg_at_k(retrieved_ids: List[str], graded_relevance: Dict[str, int], k: int) -> float:
#     """
#     Discounted Cumulative Gain.
#
#     Công thức: sum(rel_i / log2(i+1)) với i = rank từ 1
#     Doc relevant ở rank 1 đóng góp nhiều hơn rank 5.
#     Nếu graded_relevance chỉ có 0/1 (binary) thì DCG ≈ Precision@K nhưng có discount.
#     """
#     dcg = 0.0
#     for rank, doc_id in enumerate(retrieved_ids[:k], start=1):
#         rel = graded_relevance.get(doc_id, 0)
#         if rel > 0:
#             dcg += rel / math.log2(rank + 1)
#     return dcg

def dcg_at_k(retrieved_ids, graded_relevance, k):
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        rel = graded_relevance.get(doc_id, 0)
        if rel > 0:
            dcg += (2 ** rel - 1) / math.log2(i + 2)
    return dcg


def ndcg_at_k(retrieved_ids: List[str], graded_relevance: Dict[str, int], k: int) -> float:
    """
    Normalized DCG — chia cho IDCG (perfect ranking).

    IDCG: giả sử retriever trả về đúng thứ tự relevance giảm dần → ceiling.
    nDCG = 1.0 nghĩa là retriever xếp hạng hoàn hảo.
    nDCG = 0.0 nghĩa là không tìm được doc nào relevant.
    """
    actual_dcg = dcg_at_k(retrieved_ids, graded_relevance, k)

    # Ideal: sắp xếp các doc có relevance > 0 theo thứ tự giảm dần
    ideal_order = sorted(
        graded_relevance.keys(),
        key=lambda x: graded_relevance[x],
        reverse=True
    )
    ideal_dcg = dcg_at_k(ideal_order, graded_relevance, k)

    if ideal_dcg == 0.0:
        return 0.0
    return min(actual_dcg / ideal_dcg, 1.0)  # clamp an toàn


def average_metrics(scores: List[Dict]) -> Dict[str, float]:
    """Tính trung bình tất cả các chỉ số từ list kết quả từng query."""
    if not scores:
        return {}
    keys = [k for k in scores[0].keys() if k != "query"]
    return {k: sum(s[k] for s in scores) / len(scores) for k in keys}
