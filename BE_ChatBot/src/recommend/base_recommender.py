"""
recommend/base_recommender.py
Abstract base class cho tất cả các chiến lược Recommend.
Áp dụng Strategy Pattern — dễ swap giữa content-based, location-based, hybrid.
"""
from abc import ABC, abstractmethod
from src.core.schemas import Place, TripRequest


class BaseRecommender(ABC):
    """
    Interface chung cho mọi recommender.
    Input : danh sách Place (đã qua Reranker) + TripRequest
    Output: danh sách Place đã được score & sắp xếp
    """

    @abstractmethod
    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Tính recommend_score cho từng Place, trả về list đã sort descending.
        """
        pass

    def filter_top_k(self, places: list[Place], k: int) -> list[Place]:
        """Giữ lại top-k sau khi score. Có thể override nếu cần logic đặc biệt."""
        # TODO: sort by recommend_score desc, slice [:k]
        pass