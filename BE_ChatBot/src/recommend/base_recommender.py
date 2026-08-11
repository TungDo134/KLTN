"""
recommend/base_recommender.py
Abstract base class cho tất cả các chiến lược Recommend.
Dễ swap giữa content-based, location-based, hybrid.
"""

from abc import ABC, abstractmethod

from src.schemas import Place, TripRequest


class BaseRecommender(ABC):
    """
    - Interface chung cho mọi recommender.
    - Input : danh sách Place (đã qua Reranker) + TripRequest
    - Output: danh sách Place đã được score & sắp xếp
    """

    @abstractmethod
    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Tinh recommend_score cho ~ Place, tra ve list da sort descending.
        """
        pass

    def filter_top_k(self, places: list[Place], k: int) -> list[Place]:
        """Giu lai top-k sau khi score"""
        return sorted(places, key=lambda place: place.recommend_score, reverse=True)[:k]
