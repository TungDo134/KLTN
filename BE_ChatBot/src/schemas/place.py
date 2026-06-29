from dataclasses import dataclass
from typing import Optional


@dataclass
class Place:
    place_id: str
    name: str
    region: str
    lat: float
    lng: float
    tags: list[str]
    rating: float
    avg_duration_minutes: int
    opening_hours: Optional[str]
    description: Optional[str]
    place_type: str = ""
    address: Optional[str] = None
    rating_count: int = 0
    rating_is_reliable: bool = False
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    entrance_fee: float = 0.0
    best_time: Optional[str] = None
    source_url: Optional[str] = None
    rag_score: float = 0.0
    rerank_score: float = 0.0
    recommend_score: float = 0.0
