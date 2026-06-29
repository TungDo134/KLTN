"""
recommend/location_based.py
Location-Based Recommendation: ưu tiên các địa điểm gần nhau / gần trung tâm region.

Thuật toán:
  - Tính centroid (lat_mean, lng_mean) của toàn bộ tập Place
  - Tính khoảng cách Haversine từ mỗi place đến centroid
  - Normalize khoảng cách → score (gần = score cao)
  - Cộng vào recommend_score hiện tại với trọng số LOCATION_WEIGHT

Mục đích: tránh lịch trình trải dài gây tốn thời gian di chuyển.
"""
from src.schemas import Place, TripRequest
from src.recommend.base_recommender import BaseRecommender


class LocationBasedRecommender(BaseRecommender):

    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        """
        Pseudo:
          centroid = _compute_centroid(places)
          max_dist = max(haversine(p, centroid) for p in places) or 1

          for each place in places:
            dist  = haversine(place, centroid)
            norm  = 1 - (dist / max_dist)          # gần centroid → score cao
            place.recommend_score += norm * LOCATION_WEIGHT

          return sorted(places, key=lambda p: p.recommend_score, desc=True)
        """
        # TODO: implement
        pass

    def _compute_centroid(self, places: list[Place]) -> tuple[float, float]:
        """
        Pseudo:
          lat_mean = mean(p.lat for p in places)
          lng_mean = mean(p.lng for p in places)
          return (lat_mean, lng_mean)
        """
        # TODO: implement
        pass

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Tính khoảng cách (km) giữa 2 tọa độ theo công thức Haversine.
        Pseudo:
          R = 6371  # Earth radius km
          dlat = radians(lat2 - lat1)
          dlng = radians(lng2 - lng1)
          a = sin²(dlat/2) + cos(lat1)*cos(lat2)*sin²(dlng/2)
          c = 2 * atan2(sqrt(a), sqrt(1-a))
          return R * c
        """
        # TODO: implement
        pass
