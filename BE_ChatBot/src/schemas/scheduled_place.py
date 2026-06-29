from dataclasses import dataclass

from src.schemas.place import Place


@dataclass
class ScheduledPlace:
    place: Place
    day: int
    order: int
    arrival_time: str
    departure_time: str
    travel_time_from_prev: int
