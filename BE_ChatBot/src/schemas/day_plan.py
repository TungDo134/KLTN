from dataclasses import dataclass

from src.schemas.scheduled_place import ScheduledPlace


@dataclass
class DayPlan:
    day: int
    places: list[ScheduledPlace]
    total_travel_minutes: int
    total_duration_minutes: int
