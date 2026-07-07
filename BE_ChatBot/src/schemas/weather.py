from dataclasses import dataclass


@dataclass
class WeatherAdvice:
    """`output normalize` cho cac fucntion lien quan"""

    summary: str  # mo ta tong quan thoi tiet (input vao LLM)
    risk_level: str  # nguy co thoi tiet ("low", "medium", "high", "mixed")
    should_go: str  # khuyen nghi nen hay k di
    reasons: list[str]  # li do
    suggestions: list[str]  # goi y lquan den thoi tiet
    data_source: str  #
    forecast_days_available: int  # so ngay api thuc su cover
