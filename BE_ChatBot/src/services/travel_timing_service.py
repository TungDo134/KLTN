import json
import math
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

from src.schemas.travel_timing import (
    DurationBreakdown,
    TravelTimingAdvice,
)

SUPPORTED_MODES = {"car", "motorcycle", "plane"}

NOTICE_VI = (
    "LƯU Ý: Thời gian trên chỉ là ước tính. Hệ thống không có dữ liệu "
    "giao thông thực tế (tai nạn, đường cấm hoặc các phát sinh ngoài dự kiến,...)."
)
NOTICE_EN = (
    "NOTE: The time above is only an estimate. The system does not include "
    "real-time traffic, accidents, road closures, or unexpected disruptions."
)


class TimingClarificationError(ValueError):
    pass


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(
        character for character in text if unicodedata.category(character) != "Mn"
    )
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


class TravelTimingService:
    def __init__(self, data_path: str | Path | None = None):
        path = (
            Path(data_path)
            if data_path
            else (
                Path(__file__).resolve().parents[1]
                / "source_data"
                / "intercity_travel_times.json"
            )
        )
        with path.open("r", encoding="utf-8") as file:
            self.config = json.load(file)

        self.regions = self.config["regions"]
        self._alias_to_key: dict[str, str] = {}
        for key, profile in self.regions.items():
            aliases = [profile["name"], *profile.get("aliases", [])]
            for alias in aliases:
                self._alias_to_key[normalize_text(alias)] = key

    def normalize_region(self, value: str | None) -> str | None:
        normalized = normalize_text(value or "")
        if not normalized:
            return None
        if normalized in self.regions:
            return normalized
        return self._alias_to_key.get(normalized)

    def display_region(self, value: str | None) -> str:
        key = self.normalize_region(value)
        return self.regions[key]["name"] if key else str(value or "").strip()

    def supported_region_names(self) -> list[str]:
        return [profile["name"] for profile in self.regions.values()]

    def is_timing_requested(self, request) -> bool:
        return any(
            [
                getattr(request, "origin_region", None),
                getattr(request, "transport_mode", None),
                getattr(request, "day1_start_time", None),
                getattr(request, "time_intent", None),
                getattr(request, "auto_select_start_time", False),
                getattr(request, "flight_departure_at", None),
            ]
        )

    def extract_fields(self, raw_query: str) -> dict:
        normalized = normalize_text(raw_query)
        result = {}

        mentioned_regions = []
        for alias, key in sorted(
            self._alias_to_key.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            match = re.search(rf"\b{re.escape(alias)}\b", normalized)
            if match:
                mentioned_regions.append((match.start(), key))
        mentioned_regions.sort()

        unique_regions = []
        for _, key in mentioned_regions:
            if key not in unique_regions:
                unique_regions.append(key)

        origin_key = None
        origin_match = re.search(
            r"\b(?:xuat phat tu|khoi hanh tu|di tu|from)\s+"
            r"([^,.;]+)",
            normalized,
        )
        if origin_match:
            origin_fragment = origin_match.group(1)
            for alias, key in sorted(
                self._alias_to_key.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            ):
                if re.search(rf"\b{re.escape(alias)}\b", origin_fragment):
                    origin_key = key
                    break

        if origin_key:
            result["origin_region"] = self.regions[origin_key]["name"]
            destination_key = next(
                (key for key in unique_regions if key != origin_key),
                None,
            )
            if destination_key:
                result["region"] = self.regions[destination_key]["name"]
        elif unique_regions:
            result["region"] = self.regions[unique_regions[0]]["name"]

        mode_aliases = (
            ("may bay", "plane"),
            ("flight", "plane"),
            ("plane", "plane"),
            ("xe may", "motorcycle"),
            ("motorcycle", "motorcycle"),
            ("motorbike", "motorcycle"),
            ("o to", "car"),
            ("car", "car"),
        )
        for alias, mode in mode_aliases:
            if re.search(rf"\b{re.escape(alias)}\b", normalized):
                result["transport_mode"] = mode
                break

        iso_date = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", raw_query)
        short_date = re.search(
            r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b",
            raw_query,
        )
        if iso_date:
            result["start_date"] = iso_date.group(1)
        elif short_date:
            day = int(short_date.group(1))
            month = int(short_date.group(2))
            year = int(short_date.group(3) or date.today().year)
            try:
                candidate = date(year, month, day)
                if short_date.group(3) is None and candidate < date.today():
                    candidate = date(year + 1, month, day)
                result["start_date"] = candidate.isoformat()
            except ValueError:
                pass

        auto_select = bool(
            re.search(
                r"\b(?:tu chon gio|tu dong chon gio|gio phu hop|"
                r"recommend a time|choose a time)\b",
                normalized,
            )
        )
        if auto_select:
            result["auto_select_start_time"] = True
            result["time_intent"] = "auto_select"

        arrival_time_match = re.search(
            r"(?:bat dau tham quan|co mat tai|den diem dau|"
            r"start sightseeing|first attraction)"
            r"[^,.;]{0,50}?\b([01]?\d|2[0-3])[:h]([0-5]\d)\b",
            normalized,
        )
        departure_time_match = re.search(
            r"(?:xuat phat luc|khoi hanh luc|depart at|leave at)"
            r"[^,.;]{0,30}?\b([01]?\d|2[0-3])[:h]([0-5]\d)\b",
            normalized,
        )
        time_matches = list(
            re.finditer(r"\b([01]?\d|2[0-3])[:h]([0-5]\d)\b", normalized)
        )
        if arrival_time_match and not auto_select:
            result["day1_start_time"] = (
                f"{int(arrival_time_match.group(1)):02d}:{arrival_time_match.group(2)}"
            )
            result["time_intent"] = "arrival_first_place"
        elif departure_time_match and not auto_select:
            result["day1_start_time"] = (
                f"{int(departure_time_match.group(1)):02d}:"
                f"{departure_time_match.group(2)}"
            )
            result["time_intent"] = "departure"
        elif (
            len(time_matches) == 1
            and result.get("transport_mode") != "plane"
            and not auto_select
        ):
            time_match = time_matches[0]
            result["day1_start_time"] = (
                f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
            )

        if result.get("transport_mode") == "plane":
            flight_departure = re.search(
                r"(?:chuyen bay|bay|flight)[^,.;]{0,40}?"
                r"\b([01]?\d|2[0-3])[:h]([0-5]\d)\b",
                normalized,
            )
            if flight_departure:
                result["flight_departure_at"] = (
                    f"{int(flight_departure.group(1)):02d}:{flight_departure.group(2)}"
                )

            duration_patterns = {
                "airport_transfer_minutes": (
                    r"(?:toi|den|ra) san bay[^,.;]{0,30}?"
                    r"(\d+)\s*(?:phut|minutes?)"
                ),
                "flight_duration_minutes": (
                    r"(?:thoi gian bay|bay mat|flight duration)[^,.;]{0,20}?"
                    r"(\d+)\s*(?:phut|minutes?)"
                ),
                "destination_transfer_minutes": (
                    r"(?:tu san bay den|san bay toi)[^,.;]{0,30}?"
                    r"(\d+)\s*(?:phut|minutes?)"
                ),
            }
            for field, pattern in duration_patterns.items():
                match = re.search(pattern, normalized)
                if match:
                    result[field] = int(match.group(1))

        return result

    def validate_request(self, request) -> list[str]:
        missing = []
        destination_key = self.normalize_region(getattr(request, "region", None))
        origin_key = self.normalize_region(getattr(request, "origin_region", None))
        mode = str(getattr(request, "transport_mode", "") or "").strip().lower()
        time_intent = str(getattr(request, "time_intent", "") or "").strip()

        if not destination_key:
            missing.append("destination_region")
        if not origin_key:
            missing.append("origin_region")
        if mode not in SUPPORTED_MODES:
            missing.append("transport_mode")
        if not self._parse_date(getattr(request, "start_date", None)):
            missing.append("start_date")
        if not self._parse_time(getattr(request, "day1_start_time", None)):
            if not getattr(request, "auto_select_start_time", False):
                missing.append("day1_start_time")
        if time_intent not in {"arrival_first_place", "auto_select"}:
            missing.append("time_intent")

        if mode == "plane" and origin_key and destination_key:
            origin_plane = bool(self.regions[origin_key].get("plane_supported"))
            destination_plane = bool(
                self.regions[destination_key].get("plane_supported")
            )
            has_user_flight_duration = self._positive_int(
                getattr(request, "flight_duration_minutes", None)
            )
            if (
                not origin_plane or not destination_plane
            ) and not has_user_flight_duration:
                missing.append("plane_details")

        return list(dict.fromkeys(missing))

    def clarification_reply(self, request, language: str = "vi") -> str | None:
        missing = self.validate_request(request)
        if not missing:
            return None

        is_english = language == "en"
        labels = {
            "destination_region": (
                "a supported destination"
                if is_english
                else "điểm đến thuộc 1 trong 6 vùng hỗ trợ"
            ),
            "origin_region": (
                "the departure city" if is_english else "thành phố xuất phát"
            ),
            "transport_mode": (
                "the transport mode: car, motorcycle, or plane"
                if is_english
                else "phương tiện: ô tô, xe máy hoặc máy bay"
            ),
            "start_date": (
                "the itinerary start date" if is_english else "ngày bắt đầu itinerary"
            ),
            "day1_start_time": (
                "the desired time to start the first attraction"
                if is_english
                else "giờ muốn bắt đầu tham quan điểm đầu tiên"
            ),
            "time_intent": (
                "whether the stated time is the departure time or the first-attraction time"
                if is_english
                else "xác nhận giờ đã nêu là giờ xuất phát hay giờ bắt đầu tham quan"
            ),
            "plane_details": (
                "the flight duration for a route without a supported airport profile"
                if is_english
                else "thời gian bay cho tuyến chưa có profile sân bay cố định"
            ),
        }

        if is_english:
            lines = [
                "To calculate the departure time before creating the itinerary, "
                "please provide:",
                *[f"- {labels[item]}" for item in missing],
                "Supported regions: " + ", ".join(self.supported_region_names()) + ".",
            ]
        else:
            lines = [
                "Để tính giờ khởi hành trước khi tạo lịch trình, cần bổ sung:",
                *[f"- {labels[item]}" for item in missing],
                "Các vùng hỗ trợ: " + ", ".join(self.supported_region_names()) + ".",
            ]
        return "\n".join(lines)

    def build_advice(
        self,
        request,
        first_place,
        language: str = "vi",
    ) -> TravelTimingAdvice:
        origin_key = self.normalize_region(request.origin_region)
        destination_key = self.normalize_region(request.region)
        if not origin_key or not destination_key:
            raise TimingClarificationError(
                self.clarification_reply(request, language) or ""
            )

        mode = str(request.transport_mode).lower()
        target_date = self._parse_date(request.start_date)
        target_time = self._parse_time(request.day1_start_time)
        if not target_date or not target_time:
            raise TimingClarificationError(
                self.clarification_reply(request, language) or ""
            )

        target_at = datetime.combine(target_date, target_time)
        local_minutes = self._local_transfer_minutes(
            destination_key,
            first_place,
            mode,
        )

        if mode == "plane":
            return self._build_plane_advice(
                request=request,
                origin_key=origin_key,
                destination_key=destination_key,
                first_place=first_place,
                target_at=target_at,
                local_minutes=local_minutes,
                language=language,
            )

        driving_minutes, rest_minutes, safety_minutes = self._road_duration_breakdown(
            origin_key, destination_key, mode
        )
        total_minutes = driving_minutes + rest_minutes + local_minutes + safety_minutes
        departure_at = target_at - timedelta(minutes=total_minutes)
        departure_at = self._floor_to_five_minutes(departure_at)
        safe_start = departure_at - timedelta(minutes=30)

        breakdown = DurationBreakdown(
            intercity_travel_minutes=driving_minutes,
            planned_rest_minutes=rest_minutes,
            local_transfer_minutes=local_minutes,
            safety_buffer_minutes=safety_minutes,
        )
        return TravelTimingAdvice(
            advice_level="specific",
            applies_to="day_1_first_place",
            origin_region=self.regions[origin_key]["name"],
            destination_region=self.regions[destination_key]["name"],
            mode=mode,
            recommended_departure_at=self._iso(departure_at),
            safe_departure_window_start=self._iso(safe_start),
            safe_departure_window_end=self._iso(departure_at),
            target_first_place=str(getattr(first_place, "name", "") or ""),
            target_arrival_at=self._iso(target_at),
            duration_breakdown=breakdown,
            calculation_basis="static_profile",
            confidence="low",
            uncertainty_notice=NOTICE_EN if language == "en" else NOTICE_VI,
        )

    def render_markdown(
        self,
        advice: TravelTimingAdvice,
        language: str = "vi",
    ) -> str:
        departure = self._display_datetime(advice.recommended_departure_at)
        safe_start = self._display_datetime(advice.safe_departure_window_start)
        safe_end = self._display_datetime(advice.safe_departure_window_end)
        if language == "en":
            return (
                f"\n\n### Departure advice\n"
                f"- Recommended departure: **{departure}**\n"
                f"- Safe departure window: **{safe_start} – {safe_end}**\n"
                f"- Route: {advice.origin_region} → {advice.destination_region}\n"
                f"- First stop: {advice.target_first_place}\n\n"
                f"> **{advice.uncertainty_notice}**"
            )
        return (
            f"\n\n### Tư vấn khởi hành\n"
            f"- Khởi hành đề xuất: **{departure}**\n"
            f"- Khoảng khởi hành an toàn: **{safe_start} – {safe_end}**\n"
            f"- Tuyến: {advice.origin_region} → {advice.destination_region}\n"
            f"- Điểm đầu tiên: {advice.target_first_place}\n\n"
            f"> **{advice.uncertainty_notice}**"
        )

    def _build_plane_advice(
        self,
        request,
        origin_key: str,
        destination_key: str,
        first_place,
        target_at: datetime,
        local_minutes: int,
        language: str,
    ) -> TravelTimingAdvice:
        plane = self.config["plane_profile"]
        user_origin_transfer = self._positive_int(
            getattr(request, "airport_transfer_minutes", None)
        )
        user_flight_minutes = self._positive_int(
            getattr(request, "flight_duration_minutes", None)
        )
        user_destination_transfer = self._positive_int(
            getattr(request, "destination_transfer_minutes", None)
        )

        origin_transfer = user_origin_transfer or int(
            self.regions[origin_key]["airport_transfer_minutes"]
        )
        destination_transfer = user_destination_transfer or int(
            self.regions[destination_key]["airport_transfer_minutes"]
        )
        flight_minutes = user_flight_minutes or self._estimated_flight_minutes(
            origin_key,
            destination_key,
        )
        check_in_minutes = int(plane["check_in_minutes"])
        safety_minutes = int(plane["safety_buffer_minutes"])

        supplied_count = sum(
            value is not None
            for value in [
                user_origin_transfer,
                user_flight_minutes,
                user_destination_transfer,
                getattr(request, "flight_departure_at", None),
            ]
        )
        calculation_basis = (
            "static_profile"
            if supplied_count == 0
            else "user_input"
            if supplied_count == 4
            else "hybrid"
        )
        confidence = "medium" if calculation_basis == "user_input" else "low"

        flight_departure = self._parse_flight_datetime(
            getattr(request, "flight_departure_at", None),
            target_at,
            flight_minutes + destination_transfer + local_minutes,
        )
        if flight_departure:
            arrival_first_place = flight_departure + timedelta(
                minutes=flight_minutes + destination_transfer + local_minutes
            )
            if arrival_first_place > target_at:
                if language == "en":
                    message = (
                        "The provided flight would arrive after the requested "
                        "first-attraction time. Please change the flight or the "
                        "day-one start time."
                    )
                else:
                    message = (
                        "Chuyến bay đã cung cấp sẽ đến sau giờ bắt đầu tham quan. "
                        "Cần đổi chuyến bay hoặc giờ bắt đầu ngày 1."
                    )
                raise TimingClarificationError(message)
            departure_at = flight_departure - timedelta(
                minutes=origin_transfer + check_in_minutes + safety_minutes
            )
        else:
            total_minutes = (
                origin_transfer
                + check_in_minutes
                + flight_minutes
                + destination_transfer
                + local_minutes
                + safety_minutes
            )
            departure_at = target_at - timedelta(minutes=total_minutes)

        departure_at = self._floor_to_five_minutes(departure_at)
        safe_start = departure_at - timedelta(minutes=30)
        breakdown = DurationBreakdown(
            origin_airport_transfer_minutes=origin_transfer,
            check_in_minutes=check_in_minutes,
            flight_minutes=flight_minutes,
            destination_airport_transfer_minutes=destination_transfer,
            local_transfer_minutes=local_minutes,
            safety_buffer_minutes=safety_minutes,
        )
        return TravelTimingAdvice(
            advice_level="specific",
            applies_to="day_1_first_place",
            origin_region=self.regions[origin_key]["name"],
            destination_region=self.regions[destination_key]["name"],
            mode="plane",
            recommended_departure_at=self._iso(departure_at),
            safe_departure_window_start=self._iso(safe_start),
            safe_departure_window_end=self._iso(departure_at),
            target_first_place=str(getattr(first_place, "name", "") or ""),
            target_arrival_at=self._iso(target_at),
            duration_breakdown=breakdown,
            calculation_basis=calculation_basis,
            confidence=confidence,
            uncertainty_notice=NOTICE_EN if language == "en" else NOTICE_VI,
        )

    def _road_duration_breakdown(
        self,
        origin_key: str,
        destination_key: str,
        mode: str,
    ) -> tuple[int, int, int]:
        if origin_key == destination_key:
            return 0, 0, 0

        profile = self.config["road_profiles"][mode]
        distance = self._region_distance(origin_key, destination_key)
        road_distance = distance * float(profile["road_factor"])
        driving = self._ceil_minutes(
            road_distance / float(profile["average_speed_kmh"]) * 60,
            15,
        )
        rest_every = int(profile["rest_every_minutes"])
        rest_count = max(0, math.ceil(driving / rest_every) - 1)
        rest = rest_count * int(profile["rest_minutes"])
        safety = self._ceil_minutes(
            min(max((driving + rest) * 0.15, 30), 120),
            15,
        )
        return driving, rest, safety

    def _local_transfer_minutes(
        self,
        destination_key: str,
        first_place,
        mode: str,
    ) -> int:
        lat = float(getattr(first_place, "lat", 0) or 0)
        lng = float(getattr(first_place, "lng", 0) or 0)
        if not lat or not lng:
            return 30

        destination = self.regions[destination_key]
        profile = self.config["local_profiles"][mode]
        distance = self._haversine(
            float(destination["latitude"]),
            float(destination["longitude"]),
            lat,
            lng,
        )
        road_distance = distance * float(profile["road_factor"])
        return max(
            5,
            self._ceil_minutes(
                road_distance / float(profile["average_speed_kmh"]) * 60,
                5,
            ),
        )

    def _estimated_flight_minutes(
        self,
        origin_key: str,
        destination_key: str,
    ) -> int:
        plane = self.config["plane_profile"]
        distance = self._region_distance(origin_key, destination_key)
        raw_minutes = distance / float(plane["average_flight_speed_kmh"]) * 60 + int(
            plane["takeoff_landing_minutes"]
        )
        return max(
            int(plane["minimum_flight_minutes"]),
            self._ceil_minutes(raw_minutes, 15),
        )

    def _region_distance(self, origin_key: str, destination_key: str) -> float:
        origin = self.regions[origin_key]
        destination = self.regions[destination_key]
        return self._haversine(
            float(origin["latitude"]),
            float(origin["longitude"]),
            float(destination["latitude"]),
            float(destination["longitude"]),
        )

    def _haversine(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:
        radius = 6371.0
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        value = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(delta_lng / 2) ** 2
        )
        return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))

    def _parse_date(self, value) -> date | None:
        if not value:
            return None
        text = str(value).strip()
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, pattern).date()
            except ValueError:
                continue
        return None

    def _parse_time(self, value):
        if not value:
            return None
        text = str(value).strip().lower().replace("h", ":")
        text = re.sub(r":$", ":00", text)
        for pattern in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(text, pattern).time()
            except ValueError:
                continue
        return None

    def _parse_flight_datetime(
        self,
        value,
        target_at: datetime,
        after_flight_minutes: int,
    ) -> datetime | None:
        if not value:
            return None
        text = str(value).strip()
        for pattern in (
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M",
        ):
            try:
                return datetime.strptime(text, pattern)
            except ValueError:
                continue

        parsed_time = self._parse_time(text)
        if not parsed_time:
            return None
        candidate = datetime.combine(target_at.date(), parsed_time)
        if candidate + timedelta(minutes=after_flight_minutes) > target_at:
            candidate -= timedelta(days=1)
        return candidate

    def _positive_int(self, value) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _ceil_minutes(self, value: float, step: int) -> int:
        return int(math.ceil(float(value) / step) * step)

    def _floor_to_five_minutes(self, value: datetime) -> datetime:
        return value.replace(
            minute=value.minute - value.minute % 5,
            second=0,
            microsecond=0,
        )

    def _iso(self, value: datetime) -> str:
        return value.isoformat() + "+07:00"

    def _display_datetime(self, value: str) -> str:
        clean = value.removesuffix("+07:00")
        parsed = datetime.fromisoformat(clean)
        return parsed.strftime("%H:%M %d/%m/%Y")
