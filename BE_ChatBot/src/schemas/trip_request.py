from dataclasses import dataclass
from typing import Optional


@dataclass
class TripRequest:
    raw_query: str
    region: str
    days: int
    tags: list[str]
    budget: Optional[float]
    start_date: Optional[str]
    origin_region: Optional[str] = None
    transport_mode: Optional[str] = None
    day1_start_time: Optional[str] = None
    time_intent: Optional[str] = None
    auto_select_start_time: bool = False
    flight_departure_at: Optional[str] = None
    airport_transfer_minutes: Optional[int] = None
    flight_duration_minutes: Optional[int] = None
    destination_transfer_minutes: Optional[int] = None
