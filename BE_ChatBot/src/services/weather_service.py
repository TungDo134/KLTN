from collections import Counter
from datetime import date, datetime, timedelta
from typing import Callable

import httpx
from src.schemas.weather import WeatherAdvice
from src.services.climate_data import (
    REGION_TO_ZONE,
    build_best_time_overview,
    get_climate_block,
    normalize_region,
)

WEATHER_CODE_MAP: dict[int, str] = {
    0: "trời quang",
    1: "gần như quang",
    2: "có mây rải rác",
    3: "nhiều mây",
    45: "sương mù",
    48: "sương mù băng giá",
    51: "mưa phùn nhẹ",
    53: "mưa phùn",
    55: "mưa phùn dày",
    56: "mưa phùn đóng băng nhẹ",
    57: "mưa phùn đóng băng dày",
    61: "mưa nhẹ",
    63: "mưa vừa",
    65: "mưa lớn",
    66: "mưa đóng băng nhẹ",
    67: "mưa đóng băng lớn",
    71: "tuyết nhẹ",
    73: "tuyết vừa",
    75: "tuyết lớn",
    77: "hạt tuyết",
    80: "mưa rào nhẹ",
    81: "mưa rào vừa",
    82: "mưa rào lớn",
    85: "mưa tuyết nhẹ",
    86: "mưa tuyết lớn",
    95: "giông",
    96: "giông có mưa đá nhẹ",
    99: "giông có mưa đá lớn",
}


class WeatherService:
    """Service gom toàn bộ logic lấy và chuẩn hoá tư vấn thời tiết."""

    MAX_FORECAST_DAYS = 16
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    TIMEOUT = 5

    def __init__(self, today_provider: Callable[[], date] = date.today):
        """
        Init service + provider ngày hiện tại và cache geocode trong runtime.

        - `today_provider` giúp test deterministic mà không phụ thuộc ngày thật.
        - `_geocode_cache` tránh gọi lại API geocoding cho cùng một region.
        """
        self.today_provider = today_provider
        self._geocode_cache: dict[str, tuple[float, float]] = {}

    async def get_advice(
        self, region: str, start_date: str | None, days: int
    ) -> WeatherAdvice:
        """
        Entry point chính để GET WeatherAdvice cho 1 địa điểm + thời gian đi.

        - Thiếu ngày đi => trả tổng quan khí hậu theo mùa.
        - Ngày nằm trong range forecast => call `geocode + forecast API`
        - Ngày quá xa || API lỗi => fallback sang dữ liệu khí hậu tĩnh.
        """
        if not start_date:
            return self._build_overview(region)

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            return self._build_overview(region)
        today = self.today_provider()
        delta = (start - today).days

        if delta < 0:
            return WeatherAdvice(
                summary=f"Ngày {start_date} đã qua, không thể dự báo thời tiết.",
                risk_level="medium",
                should_go="go_with_caution",
                reasons=["ngày đi đã qua"],
                suggestions=["hãy chọn ngày trong tương lai"],
                data_source="unavailable",
                forecast_days_available=0,
            )

        end_date = start + timedelta(days=max(days - 1, 0))

        if delta <= self.MAX_FORECAST_DAYS:
            max_end_date = today + timedelta(days=self.MAX_FORECAST_DAYS)
            if end_date > max_end_date:
                end_date = max_end_date

            coords = await self._geocode(region)
            if coords:
                result = await self._fetch_forecast(
                    coords[0],
                    coords[1],
                    start_date,
                    end_date.isoformat(),
                )
                if result.data_source != "unavailable":
                    return result

            return self._lookup_seasonal(region, start.month)

        return self._lookup_seasonal(region, start.month)

    async def _geocode(self, region: str) -> tuple[float, float] | None:
        """
        Convert name location => latitude/longitude = Open-Meteo.

        - Ưu tiên `cache theo region` đã normalize.
        - Nếu không tìm được toạ độ || API lỗi => trả None để caller fallback sang dữ liệu mùa.
        """
        cache_key = normalize_region(region)
        if cache_key in self._geocode_cache:
            return self._geocode_cache[cache_key]

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    self.GEOCODE_URL,
                    params={
                        "name": region,
                        "count": 1,
                        "language": "vi",
                        "countryCode": "VN",
                    },
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            print(f"[Weather Service] Geocode failed for '{region}': {exc}")
            return None

        results = data.get("results", [])
        if not results:
            return None

        coords = (float(results[0]["latitude"]), float(results[0]["longitude"]))
        self._geocode_cache[cache_key] = coords
        return coords

    async def _fetch_forecast(
        self,
        lat: float,
        lng: float,
        start_date: str,
        end_date: str,
    ) -> WeatherAdvice:
        """
        Call Open-Meteo Forecast API (range <=16).

        Response (output raw JSON) => parse về WeatherAdvice
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    self.FORECAST_URL,
                    params={
                        "latitude": lat,
                        "longitude": lng,
                        "daily": ",".join(
                            [
                                "temperature_2m_max",
                                "temperature_2m_min",
                                "precipitation_probability_max",
                                "rain_sum",
                                "weather_code",
                                "uv_index_max",
                                "wind_speed_10m_max",
                            ]
                        ),
                        "timezone": "Asia/Ho_Chi_Minh",
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )
                response.raise_for_status()
                return self._parse_forecast(response.json(), start_date, end_date)
        except Exception as exc:
            print(f"[Weather Service] Forecast API failed: {exc}")
            return WeatherAdvice(
                summary="Không thể lấy dự báo thời tiết lúc này.",
                risk_level="medium",
                should_go="go_with_caution",
                reasons=["không thể kết nối dịch vụ thời tiết"],
                suggestions=["kiểm tra dự báo thời tiết trước khi đi"],
                data_source="unavailable",
                forecast_days_available=0,
            )

    def _parse_forecast(
        self,
        data: dict,
        start_date: str,
        end_date: str,
    ) -> WeatherAdvice:
        """
        Normalize daily forecast JSON =>  WeatherAdvice.

        Hàm tổng hợp nhiệt độ, xác suất mưa, lượng mưa, UV, gió và weather code
        thành summary, risk_level, should_go, reasons và suggestions.
        """
        daily = data.get("daily", {})
        times = daily.get("time", [])
        day_count = len(times)

        if day_count == 0:
            return WeatherAdvice(
                summary="Không có dữ liệu dự báo thời tiết cho khoảng ngày này.",
                risk_level="medium",
                should_go="go_with_caution",
                reasons=["dữ liệu dự báo rỗng"],
                suggestions=["kiểm tra lại ngày đi hoặc xem dự báo thủ công"],
                data_source="unavailable",
                forecast_days_available=0,
            )

        temp_maxs = daily.get("temperature_2m_max", [])
        temp_mins = daily.get("temperature_2m_min", [])
        precip_probs = daily.get("precipitation_probability_max", [])
        rain_sums = daily.get("rain_sum", [])
        uv_maxs = daily.get("uv_index_max", [])
        wind_maxs = daily.get("wind_speed_10m_max", [])
        weather_codes = daily.get("weather_code", [])

        temp_low = min(temp_mins) if temp_mins else 0
        temp_high = max(temp_maxs) if temp_maxs else 0
        avg_precip = sum(precip_probs) / len(precip_probs) if precip_probs else 0
        max_rain = max(rain_sums) if rain_sums else 0
        max_uv = max(uv_maxs) if uv_maxs else 0
        max_wind = max(wind_maxs) if wind_maxs else 0

        if avg_precip > 70 or max_rain > 20 or max_wind >= 40:
            risk_level = "high"
            should_go = "not_recommended"
        elif avg_precip > 40 or max_rain > 10 or max_uv >= 8 or max_wind >= 30:
            risk_level = "medium"
            should_go = "go_with_caution"
        else:
            risk_level = "low"
            should_go = "recommended"

        weather_desc = self._describe_weather_codes(weather_codes)
        summary = (
            f"{start_date} đến {end_date}: {weather_desc}, "
            f"{temp_low:.0f}-{temp_high:.0f}°C, "
            f"xác suất mưa trung bình {avg_precip:.0f}%"
        )
        if max_rain > 0:
            summary += f", mưa cao nhất {max_rain:.1f}mm"
        if max_uv >= 8:
            summary += f", UV cao ({max_uv:.0f})"
        if max_wind >= 30:
            summary += f", gió mạnh ({max_wind:.0f}km/h)"

        reasons = []
        suggestions = []
        if avg_precip > 40:
            reasons.append(f"xác suất mưa trung bình {avg_precip:.0f}%")
            suggestions.append("mang áo mưa hoặc ô")
        if max_rain > 10:
            reasons.append(f"có ngày mưa tới {max_rain:.1f}mm")
            suggestions.append("ưu tiên điểm trong nhà vào ngày mưa lớn")
        if max_uv >= 8:
            reasons.append(f"UV index cao ({max_uv:.0f})")
            suggestions.append("mang kem chống nắng SPF50+")
        if max_wind >= 30:
            reasons.append(f"gió mạnh tới {max_wind:.0f}km/h")
            suggestions.append("tránh hoạt động ngoài trời khi gió mạnh")
        if temp_high >= 35:
            reasons.append(f"nhiệt độ cao ({temp_high:.0f}°C)")
            suggestions.append("uống nhiều nước, tránh nắng 11h-14h")

        if not reasons:
            reasons.append("thời tiết tương đối ổn định")

        return WeatherAdvice(
            summary=summary,
            risk_level=risk_level,
            should_go=should_go,
            reasons=reasons,
            suggestions=suggestions,
            data_source="forecast_api",
            forecast_days_available=day_count,
        )

    def _lookup_seasonal(self, region: str, month: int) -> WeatherAdvice:
        """
        Lấy tư vấn thời tiết theo dữ liệu khí hậu tĩnh của region và tháng.

        Dùng khi ngày đi nằm ngoài range forecast 16 ngày, hoặc khi forecast API
        không khả dụng nhưng vẫn còn dữ liệu khí hậu mùa vụ để fallback.
        """
        block = get_climate_block(region, month)
        if not block:
            return WeatherAdvice(
                summary=f"Không có dữ liệu khí hậu chi tiết cho '{region}'.",
                risk_level="mixed",
                should_go="depends_on_date",
                reasons=["vùng chưa có trong dữ liệu khí hậu tĩnh"],
                suggestions=[
                    "hãy kiểm tra dự báo thời tiết gần ngày đi để có thông tin chính xác hơn"
                ],
                data_source="unavailable",
                forecast_days_available=0,
            )

        summary = (
            f"{region} tháng {month}: {block['label']}, "
            f"{block['temp_range']}, {block['rain']}. {block['notes']}"
        )
        return WeatherAdvice(
            summary=summary,
            risk_level=block["risk_level"],
            should_go=block["should_go"],
            reasons=[block["notes"]],
            suggestions=block["suggestions"],
            data_source="seasonal_general",
            forecast_days_available=0,
        )

    def _build_overview(self, region: str) -> WeatherAdvice:
        """
        Gen overview khí hậu theo vùng khi user chưa cung cấp ngày đi.

        Output giúp LLM trả lời theo kiểu định hướng mùa đẹp/mùa cần tránh và
        gợi ý user cung cấp thời gian cụ thể hơn.
        """
        normalized = normalize_region(region)
        zone = REGION_TO_ZONE.get(normalized)
        if not zone:
            return WeatherAdvice(
                summary=f"Không có dữ liệu khí hậu chi tiết cho '{region}'.",
                risk_level="mixed",
                should_go="depends_on_date",
                reasons=["vùng chưa có trong dữ liệu khí hậu tĩnh"],
                suggestions=[
                    "hãy cho biết thời gian và địa điểm cụ thể hơn để tư vấn chính xác hơn"
                ],
                data_source="best_time_overview",
                forecast_days_available=0,
            )

        overview = build_best_time_overview(zone)
        return WeatherAdvice(
            summary=f"Tổng quan khí hậu {region}:\n{overview}",
            risk_level="mixed",
            should_go="depends_on_date",
            reasons=["chưa có ngày cụ thể để đánh giá dự báo thời tiết"],
            suggestions=[
                "hãy cho biết thời gian dự kiến để tư vấn thời tiết chính xác hơn"
            ],
            data_source="best_time_overview",
            forecast_days_available=0,
        )

    def _describe_weather_codes(self, codes: list[int]) -> str:
        """
        Convert list WMO weather code =>  short des tiếng Việt.

        Dùng mã xuất hiện nhiều nhất trong forecast period để mô tả trạng thái
        thời tiết đại diện cho toàn khoảng ngày.
        """
        if not codes:
            return "không rõ trạng thái thời tiết"

        most_common_code = Counter(codes).most_common(1)[0][0]
        return WEATHER_CODE_MAP.get(
            most_common_code, f"mã thời tiết {most_common_code}"
        )
