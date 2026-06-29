from dataclasses import dataclass

from src.schemas.day_plan import DayPlan
from src.schemas.trip_request import TripRequest


@dataclass
class TripPlan:
    trip_request: TripRequest
    days: list[DayPlan]
    total_places: int
