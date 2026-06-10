"""
core/schemas.py
Định nghĩa các Data Transfer Objects (DTO) / dataclasses dùng chung
giữa các module: RAG → Recommend → Planning → Generation
"""

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────
# 1. INPUT từ User (sau khi LLM extract)
# ─────────────────────────────────────────
@dataclass
class TripRequest:
    """
    Kết quả sau khi LLM phân tích câu hỏi tự nhiên của user.
    Ví dụ: "Tôi muốn đi Đà Lạt 2 ngày, thích cà phê và thác nước, budget 2 triệu"
    """

    raw_query: str  # câu gốc của user
    region: str  # vd: "Đà Lạt", "Hà Nội"
    days: int  # số ngày
    tags: list[str]  # vd: ["cafe", "thác nước", "thiên nhiên"]
    budget: Optional[float]  # tổng ngân sách (VND), None nếu không rõ
    start_date: Optional[str]  # ISO date string, None nếu không rõ


# ─────────────────────────────────────────
# 2. ĐỊA ĐIỂM (document từ ChromaDB)
# ─────────────────────────────────────────
@dataclass
class Place:
    """
    Đại diện cho một địa điểm du lịch được lấy từ ChromaDB / nguồn dữ liệu.
    """

    place_id: str
    name: str
    region: str
    lat: float
    lng: float
    tags: list[str]  # vd: ["cafe", "view", "check-in"]
    rating: float  # 0.0 – 5.0
    avg_duration_minutes: int  # thời gian tham quan trung bình
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
    rag_score: float = 0.0  # score từ ChromaDB similarity search
    rerank_score: float = 0.0  # score sau Reranker
    recommend_score: float = 0.0  # score sau Recommender


# ─────────────────────────────────────────
# 3. OUTPUT từ Recommender
# ─────────────────────────────────────────
@dataclass
class RecommendResult:
    places: list[Place]
    trip_request: TripRequest


# ─────────────────────────────────────────
# 4. OUTPUT từ Graph-based Planning
# ─────────────────────────────────────────
@dataclass
class ScheduledPlace:
    """Một địa điểm đã được sắp xếp vào lịch trình."""

    place: Place
    day: int  # ngày thứ mấy (1-based)
    order: int  # thứ tự trong ngày (1-based)
    arrival_time: str  # vd: "08:30"
    departure_time: str  # vd: "10:00"
    travel_time_from_prev: int  # phút di chuyển từ điểm trước


@dataclass
class DayPlan:
    day: int
    places: list[ScheduledPlace]
    total_travel_minutes: int
    total_duration_minutes: int


@dataclass
class TripPlan:
    trip_request: TripRequest
    days: list[DayPlan]
    total_places: int
