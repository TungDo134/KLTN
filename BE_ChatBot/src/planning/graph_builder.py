"""
planning/graph_builder.py
Xây dựng đồ thị có trọng số (weighted graph) từ danh sách địa điểm.

Cấu trúc đồ thị:
  - Node  : mỗi Place (place_id là key)
  - Edge  : cặp (place_i, place_j) với weight = travel_time (phút) hoặc distance (km)
  - Đồ thị vô hướng (undirected), đầy đủ (complete graph — mọi cặp đều có edge)

Dùng thư viện: networkx (hoặc dict thuần)
"""
from src.schemas import Place


class GraphBuilder:

    def build(self, places: list[Place], weight_mode: str = "time") -> dict:
        """
        Xây đồ thị dạng adjacency dict:
          graph = {
            place_id_A: {place_id_B: weight_AB, place_id_C: weight_AC, ...},
            place_id_B: {place_id_A: weight_AB, ...},
            ...
          }

        weight_mode:
          "time"     → weight = ước tính thời gian di chuyển (phút)
          "distance" → weight = khoảng cách Haversine (km)

        Pseudo:
          graph = defaultdict(dict)
          for i, pi in enumerate(places):
            for j, pj in enumerate(places):
              if i == j: continue
              w = _compute_weight(pi, pj, weight_mode)
              graph[pi.place_id][pj.place_id] = w
          return graph
        """
        # TODO: implement
        pass

    def _compute_weight(self, a: Place, b: Place, mode: str) -> float:
        """
        Pseudo:
          dist_km = haversine(a.lat, a.lng, b.lat, b.lng)
          if mode == "distance": return dist_km
          if mode == "time":
            AVG_SPEED_KMH = 30
            return (dist_km / AVG_SPEED_KMH) * 60  # → phút
        """
        # TODO: implement (reuse haversine từ location_based hoặc utils)
        pass

    def add_node_weights(self, graph: dict, places: list[Place]) -> dict:
        """
        Gắn thêm metadata (avg_duration, rating) vào từng node để Scheduler dùng.
        Pseudo:
          node_data = {p.place_id: {"duration": p.avg_duration_minutes, "rating": p.rating}
                       for p in places}
          return {"graph": graph, "nodes": node_data}
        """
        # TODO: implement
        pass
