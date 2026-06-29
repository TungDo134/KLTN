from dataclasses import dataclass

from src.schemas.place import Place
from src.schemas.trip_request import TripRequest


@dataclass
class RecommendResult:
    places: list[Place]
    trip_request: TripRequest
