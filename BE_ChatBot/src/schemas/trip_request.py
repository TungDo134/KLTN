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
