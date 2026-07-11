from __future__ import annotations

import math
from statistics import mean
from typing import Iterable


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / k


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0 or not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(relevant_ids)


def dcg_at_k(retrieved_ids: list[str], graded_relevance: dict[str, int], k: int) -> float:
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        rel = graded_relevance.get(doc_id, 0)
        if rel > 0:
            dcg += (2**rel - 1) / math.log2(i + 2)
    return dcg


def ndcg_at_k(retrieved_ids: list[str], graded_relevance: dict[str, int], k: int) -> float:
    actual_dcg = dcg_at_k(retrieved_ids, graded_relevance, k)
    ideal_order = sorted(graded_relevance, key=lambda doc_id: graded_relevance[doc_id], reverse=True)
    ideal_dcg = dcg_at_k(ideal_order, graded_relevance, k)
    if ideal_dcg <= 0:
        return 0.0
    return min(actual_dcg / ideal_dcg, 1.0)


def average(values: Iterable[float]) -> float:
    values = list(values)
    return mean(values) if values else 0.0


def percentile(values: Iterable[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if p <= 0:
        return ordered[0]
    if p >= 100:
        return ordered[-1]
    rank = (len(ordered) - 1) * (p / 100)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    lower_value = ordered[lower]
    upper_value = ordered[upper]
    return lower_value + (upper_value - lower_value) * (rank - lower)


def latency_summary(values_ms: Iterable[float]) -> dict[str, float]:
    values = list(values_ms)
    if not values:
        return {"avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0, "p95_ms": 0.0}
    return {
        "avg_ms": average(values),
        "min_ms": min(values),
        "max_ms": max(values),
        "p95_ms": percentile(values, 95),
    }

