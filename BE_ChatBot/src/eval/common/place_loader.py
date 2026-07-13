from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.eval.common.config import EXPECTED_PLACE_FILES, PLACE_DATA_DIR, REGION_ALIASES
from src.eval.common.path_utils import normalize_text, read_json
from src.eval.common.schemas import PlaceRecord


def canonical_region(region: str) -> str:
    normalized = normalize_text(region)
    return REGION_ALIASES.get(normalized, region.strip())


def get_nested(data: dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def flatten_place(place: dict[str, Any], source_file: str) -> PlaceRecord:
    rating = place.get("rating") or {}
    geo = place.get("geo") or {}
    time_info = place.get("time") or {}
    tags = place.get("tags") or []

    return PlaceRecord(
        id=str(place.get("id") or ""),
        name=str(place.get("name") or ""),
        region=str(place.get("region") or ""),
        canonical_region=canonical_region(str(place.get("region") or "")),
        place_type=str(place.get("type") or ""),
        tags=[str(tag) for tag in tags],
        rating_score=rating.get("score"),
        rating_review_count=rating.get("review_count"),
        lat=geo.get("lat"),
        lng=geo.get("lng"),
        open_time=time_info.get("open"),
        close_time=time_info.get("close"),
        avg_duration_minutes=place.get("avg_duration_minutes"),
        entrance_fee=place.get("entrance_fee"),
        description=place.get("description"),
        best_time=place.get("best_time"),
        source_file=source_file,
        raw=place,
    )


def load_place_records() -> tuple[list[PlaceRecord], list[str]]:
    places: list[PlaceRecord] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    for file_name, expected_region in EXPECTED_PLACE_FILES.items():
        path = PLACE_DATA_DIR / file_name
        if not path.exists():
            warnings.append(f"Missing expected data file: {file_name}")
            continue

        raw_places = read_json(path)
        if not isinstance(raw_places, list):
            warnings.append(f"{file_name} is not a JSON array")
            continue

        if len(raw_places) != 100:
            warnings.append(f"{file_name} has {len(raw_places)} records, expected 100")

        for place in raw_places:
            record = flatten_place(place, file_name)
            if not record.id:
                warnings.append(f"{file_name} contains a place without id")
                continue
            if record.id in seen_ids:
                warnings.append(f"Duplicate place id skipped: {record.id}")
                continue
            seen_ids.add(record.id)

            if canonical_region(record.region) != expected_region:
                warnings.append(
                    f"{record.id} region '{record.region}' differs from expected file region '{expected_region}'"
                )
            places.append(record)

    return places, warnings


def build_place_indexes(places: list[PlaceRecord]) -> dict[str, Any]:
    by_id = {place.id: place for place in places}
    by_name = {normalize_text(place.name): place for place in places if place.name}
    by_region: dict[str, list[PlaceRecord]] = defaultdict(list)
    all_tags: set[str] = set()
    all_types: set[str] = set()

    for place in places:
        by_region[place.canonical_region].append(place)
        if place.place_type:
            all_types.add(normalize_text(place.place_type))
        for tag in place.tags:
            normalized_tag = normalize_text(tag)
            if normalized_tag:
                all_tags.add(normalized_tag)

    return {
        "by_id": by_id,
        "by_name": by_name,
        "by_region": dict(by_region),
        "all_tags": all_tags,
        "all_types": all_types,
    }
