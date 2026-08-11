"""
recommend/location_based.py
Location-Based Recommendation: ưu tiên các địa điểm gần nhau / gần trung tâm region.

Thuật toán:
  - Tính centroid (lat_mean, lng_mean) của toàn bộ tập Place
  - Tính khoảng cách Haversine (khoảng cách đường chim bay giữa hai tọa độ trên bề mặt Trái Đất)
  từ mỗi place đến centroid
  - Normalize khoảng cách → score (gần = score cao)
  - Cộng vào recommend_score hiện tại với trọng số LOCATION_WEIGHT

Mục đích: tránh lịch trình trải dài gây tốn thời gian di chuyển.
"""

import math

from src.recommend.base_recommender import BaseRecommender
from src.schemas import Place, TripRequest


class LocationBasedRecommender(BaseRecommender):
    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Tinh `raw location` dua tren khoang cach toi centroid
        """
        if not places:
            return places

        centroid_lat, centroid_lng = self._compute_centroid(places)
        distances = [
            self._haversine(place.lat, place.lng, centroid_lat, centroid_lng)
            for place in places
        ]
        max_dist = max(distances) or 1.0

        for place, distance in zip(places, distances):
            location_score = 1.0 - (distance / max_dist)
            place.distance_to_candidate_centroid_km = distance
            place.location_recommend_score = location_score
            place.recommend_score = location_score

        return sorted(places, key=lambda place: place.recommend_score, reverse=True)

    def _compute_centroid(self, places: list[Place]) -> tuple[float, float]:
        """
        Tinh `toa do trung binh` cua tap places
        """
        lat_mean = sum(place.lat for place in places) / len(places)
        lng_mean = sum(place.lng for place in places) / len(places)
        return lat_mean, lng_mean

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        -  Haversine: Khoảng cách đường chim bay giữa hai tọa độ trên bề mặt Trái Đất
        - VD:
            - (lat1, lng1) ----- khoảng cách km ----- (lat2, lng2)
        """
        earth_radius_km = 6371.0

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return earth_radius_km * c
