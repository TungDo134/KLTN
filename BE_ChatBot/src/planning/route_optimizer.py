"""
planning/route_optimizer.py
Tối ưu thứ tự ghé thăm địa điểm trong một ngày — giải bài TSP xấp xỉ.

Thuật toán được hỗ trợ:
  1. GreedyNearestNeighbor (mặc định, O(n²), nhanh)
  2. Dijkstra-based path  (nếu có điểm bắt đầu cố định)
  3. (Tương lai) 2-opt improvement

Đầu vào : graph (adjacency dict từ GraphBuilder) + danh sách place_id cần thăm
Đầu ra  : list[place_id] — thứ tự tối ưu
"""
from src.core.schemas import Place


class RouteOptimizer:

    def optimize(
        self,
        places: list[Place],
        graph: dict,
        algorithm: str = "greedy",
        start_place_id: str | None = None,
    ) -> list[str]:
        """
        Entry point. Chọn thuật toán theo `algorithm` param.
        Pseudo:
          if algorithm == "greedy":
            return _greedy_nearest_neighbor(places, graph, start_place_id)
          elif algorithm == "dijkstra":
            return _dijkstra_path(places, graph, start_place_id)
          else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        """
        # TODO: implement
        pass

    # ── Greedy Nearest Neighbor ────────────────────────────────────────────────
    def _greedy_nearest_neighbor(
        self, places: list[Place], graph: dict, start_id: str | None
    ) -> list[str]:
        """
        Pseudo:
          unvisited = set(p.place_id for p in places)
          current   = start_id or pick place with highest recommend_score
          route     = [current]
          unvisited.remove(current)

          while unvisited:
            nearest = min(unvisited, key=lambda nid: graph[current][nid])
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest

          return route
        """
        # TODO: implement
        pass

    # ── Dijkstra shortest path ────────────────────────────────────────────────
    def _dijkstra_path(
        self, places: list[Place], graph: dict, start_id: str
    ) -> list[str]:
        """
        Tìm đường đi ngắn nhất từ start_id qua tất cả nodes (approximation).
        Pseudo:
          Dùng heapq / networkx shortest_path.
          Ghép các đoạn shortest_path lại thành 1 hành trình hoàn chỉnh.
        """
        # TODO: implement
        pass

    # ── (Future) 2-opt local search ───────────────────────────────────────────
    def _two_opt_improve(self, route: list[str], graph: dict) -> list[str]:
        """
        Pseudo:
          improved = True
          while improved:
            improved = False
            for i in range(1, len(route)-1):
              for j in range(i+1, len(route)):
                new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]
                if total_cost(new_route) < total_cost(route):
                  route = new_route
                  improved = True
          return route
        """
        # TODO: implement
        pass

    def total_cost(self, route: list[str], graph: dict) -> float:
        """
        Tính tổng trọng số của một route.
        Pseudo:
          return sum(graph[route[i]][route[i+1]] for i in range(len(route)-1))
        """
        # TODO: implement
        pass
