"""
planning/planner.py
Facade / Coordinator cho toàn bộ Planning module.
Nhận RecommendResult → trả về TripPlan.

FLOW nội bộ:
  RecommendResult
      ↓
  GraphBuilder.build()          → weighted graph
      ↓
  RouteOptimizer.optimize()     → ordered place_ids (global optimal order)
      ↓
  Scheduler.split_into_days()   → chia theo ngày
      ↓
  Scheduler.schedule()          → gán giờ cụ thể
      ↓
  TripPlan
"""
from src.schemas import RecommendResult, TripPlan
from src.planning.graph_builder import GraphBuilder
from src.planning.route_optimizer import RouteOptimizer
from src.planning.scheduler import Scheduler


class TripPlanner:

    def __init__(
        self,
        weight_mode: str = "time",
        route_algorithm: str = "greedy",
    ):
        self.weight_mode     = weight_mode
        self.route_algorithm = route_algorithm
        self.graph_builder   = GraphBuilder()
        self.optimizer       = RouteOptimizer()
        self.scheduler       = Scheduler()

    def plan(self, recommend_result: RecommendResult) -> TripPlan:
        """
        Entry point chính.

        Pseudo:
          places  = recommend_result.places
          request = recommend_result.trip_request

          # Bước 1: Xây đồ thị
          graph_data = graph_builder.build(places, weight_mode)
          graph      = graph_data["graph"]
          travel_matrix = graph  # adjacency dict cũng là travel matrix

          # Bước 2: Tối ưu thứ tự toàn bộ
          ordered_ids = optimizer.optimize(places, graph, route_algorithm)
          ordered_places = [place_map[pid] for pid in ordered_ids]

          # Bước 3: Chia theo ngày
          places_per_day = scheduler.split_places_into_days(ordered_places, request.days)

          # Bước 4: Lên lịch chi tiết
          trip_plan = scheduler.schedule(places_per_day, travel_matrix, request)

          return trip_plan
        """
        # TODO: implement
        pass

    def _build_place_map(self, places) -> dict:
        """
        Pseudo:
          return {p.place_id: p for p in places}
        """
        # TODO: implement
        pass
