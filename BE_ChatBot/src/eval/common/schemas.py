from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MetricRow:
    group: str
    metric_name: str
    purpose: str
    why_needed: str
    formula: str
    unit: str
    better_direction: str
    data_source: str
    sample_size: str
    value: Any
    note: str = ""

    def to_report_row(self) -> dict[str, Any]:
        return {
            "Nhóm": self.group,
            "Tên chỉ số": self.metric_name,
            "Công dụng": self.purpose,
            "Tại sao cần": self.why_needed,
            "Giá trị / Cách tính": self.formula,
            "Đơn vị": self.unit,
            "Chiều tốt": self.better_direction,
            "Nguồn dữ liệu": self.data_source,
            "Cỡ mẫu": self.sample_size,
            "Kết quả đo được": self.value,
            "Ghi chú": self.note,
        }


@dataclass
class PlaceRecord:
    id: str
    name: str
    region: str
    canonical_region: str
    place_type: str
    tags: list[str]
    rating_score: float | None
    rating_review_count: int | None
    lat: float | None
    lng: float | None
    open_time: str | None
    close_time: str | None
    avg_duration_minutes: int | None
    entrance_fee: float | None
    description: str | None
    best_time: str | None
    source_file: str
    raw: dict[str, Any] = field(repr=False)


@dataclass
class RetrievalCase:
    id: str
    query: str
    expected_region: str
    required_tags: list[str]
    optional_types: list[str]


@dataclass
class OutputCase:
    id: str
    query: str
    expected_region: str
    expected_days: int


@dataclass
class DatasetCoverageResult:
    total_places: int
    places_by_region: dict[str, int]
    unique_tags_count: int
    unique_types_count: int
    missing_metadata_rate_by_field: dict[str, float]
    avg_rating_by_region: dict[str, float | None]
    warnings: list[str]


@dataclass
class RetrievalCaseResult:
    case_id: str
    query: str
    expected_region: str
    relevant_universe_size: int
    raw_doc_ids: list[str]
    reranked_doc_ids: list[str]
    metrics_before_rerank: dict[str, float]
    metrics_after_rerank: dict[str, float]
    retrieval_latency_ms: float
    rerank_latency_ms: float
    llm_runtime: dict[str, str | None]
    rerank_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutputValidityCaseResult:
    case_id: str
    query: str
    expected_region: str
    expected_days: int
    parse_success: bool
    schema_valid: bool
    day_count_match: bool
    region_consistent: bool
    duplicate_place: bool
    required_field_completion_rate: float
    latency_ms: float
    parse_error: str | None
    llm_runtime: dict[str, str | None]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
