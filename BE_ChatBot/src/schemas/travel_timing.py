from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class DurationBreakdown:
    intercity_travel_minutes: int = 0
    planned_rest_minutes: int = 0
    origin_airport_transfer_minutes: Optional[int] = None
    check_in_minutes: Optional[int] = None
    flight_minutes: Optional[int] = None
    destination_airport_transfer_minutes: Optional[int] = None
    local_transfer_minutes: int = 0
    safety_buffer_minutes: int = 0


@dataclass
class TravelTimingAdvice:
    advice_level: str
    applies_to: str
    origin_region: str
    destination_region: str
    mode: str
    recommended_departure_at: str
    safe_departure_window_start: str
    safe_departure_window_end: str
    target_first_place: str
    target_arrival_at: str
    duration_breakdown: DurationBreakdown
    calculation_basis: str
    confidence: str
    uncertainty_notice: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        start = data.pop("safe_departure_window_start")
        end = data.pop("safe_departure_window_end")
        data["safe_departure_window"] = {
            "start": start,
            "end": end,
        }
        return data
