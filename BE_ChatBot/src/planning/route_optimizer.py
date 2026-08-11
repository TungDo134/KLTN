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

from src.schemas import Place


class RouteOptimizer:
    def optimize(
        self,
        places: list[Place],
        graph: dict,
        algorithm: str = "greedy",
        start_place_id: str | None = None,
    ) -> list[str]:
        if not places:
            return []

        if algorithm == "greedy":
            route = self._greedy_nearest_neighbor(places, graph, start_place_id)
        elif algorithm == "dijkstra":
            # Dijkstra path requires a starting node; if not provided, pick highest recommend_score
            sid = start_place_id
            if not sid or sid not in [p.place_id for p in places]:
                sid = max(places, key=lambda p: p.recommend_score).place_id
            route = self._dijkstra_path(places, graph, sid)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Optimize with 2-opt
        if len(route) > 3:
            route = self._two_opt_improve(route, graph)

        return route

    # ── Greedy Nearest Neighbor ────────────────────────────────────────────────
    def _greedy_nearest_neighbor(
        self, places: list[Place], graph: dict, start_id: str | None
    ) -> list[str]:
        unvisited = set(p.place_id for p in places)
        if not unvisited:
            return []

        if start_id in unvisited:
            current = start_id
        else:
            current = max(places, key=lambda p: p.recommend_score).place_id

        route = [current]
        unvisited.remove(current)

        while unvisited:
            neighbors = graph.get(current, {})
            nearest = min(unvisited, key=lambda nid: neighbors.get(nid, float("inf")))
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest

        return route

    # ── Dijkstra shortest path ────────────────────────────────────────────────
    def _dijkstra_path(
        self, places: list[Place], graph: dict, start_id: str
    ) -> list[str]:
        unvisited = set(p.place_id for p in places)
        if not unvisited:
            return []

        current = start_id if start_id in unvisited else list(unvisited)[0]
        route = [current]
        unvisited.remove(current)

        while unvisited:
            best_next = None
            min_cost = float("inf")
            for nid in unvisited:
                _, cost = self._dijkstra(graph, current, nid)
                if cost < min_cost:
                    min_cost = cost
                    best_next = nid
            if best_next is None:
                best_next = unvisited.pop()
            else:
                unvisited.remove(best_next)
            route.append(best_next)
            current = best_next

        return route

    # nút thắt tính toán của djkstra để tìm đường đi ngắn nhất
    def _dijkstra(
        self, graph: dict, start: str, target: str
    ) -> tuple[list[str], float]:
        import heapq

        queue = [(0.0, start, [start])]
        visited = set()
        while queue:
            cost, node, path = heapq.heappop(queue)
            if node in visited:
                continue
            visited.add(node)
            if node == target:
                return path, cost
            for neighbor, weight in graph.get(
                node, {}
            ).items():  # duyệt qua tất cả các node kề với node hiện tại rồi đưa vào hàng đợi ưu tiên
                if neighbor not in visited:
                    heapq.heappush(queue, (cost + weight, neighbor, path + [neighbor]))
        return [], float("inf")

    # ── (Future) 2-opt local search ───────────────────────────────────────────
    def _two_opt_improve(self, route: list[str], graph: dict) -> list[str]:
        improved = True
        best_route = list(route)
        while improved:
            improved = False
            for i in range(1, len(best_route) - 1):
                for j in range(i + 1, len(best_route)):
                    new_route = (
                        best_route[:i]
                        + best_route[i : j + 1][::-1]
                        + best_route[j + 1 :]
                    )
                    if self.total_cost(new_route, graph) < self.total_cost(
                        best_route, graph
                    ):
                        best_route = new_route
                        improved = True
            if not improved:
                break
        return best_route

    def total_cost(self, route: list[str], graph: dict) -> float:
        cost = 0.0
        for i in range(len(route) - 1):
            w = graph.get(route[i], {}).get(route[i + 1])
            if w is not None:
                cost += w
        return cost
