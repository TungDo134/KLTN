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
        places  = recommend_result.places
        request = recommend_result.trip_request

        if not places:
            return TripPlan(trip_request=request, days=[], total_places=0)

        place_map = self._build_place_map(places)

        # Step 1: Build graph
        graph = self.graph_builder.build(places, self.weight_mode)
        travel_matrix = graph

        # Step 2: Global route optimization
        ordered_ids = self.optimizer.optimize(
            places=places,
            graph=graph,
            algorithm=self.route_algorithm,
            start_place_id=None #truyền djkstra ở đây
        )
        ordered_places = [place_map[pid] for pid in ordered_ids if pid in place_map]

        # Step 3: Split into days
        places_per_day = self.scheduler.split_places_into_days(ordered_places, request.days)

        # Step 4: Schedule each day with time and duration
        trip_plan = self.scheduler.schedule(places_per_day, travel_matrix, request)

        return trip_plan

    def _build_place_map(self, places) -> dict:
        return {p.place_id: p for p in places}

