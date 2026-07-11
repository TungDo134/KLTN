from __future__ import annotations

from typing import Any

from src.eval.common.config import REGION_ALIASES
from src.eval.common.path_utils import normalize_text, read_json
from src.eval.common.place_loader import canonical_region
from src.eval.common.schemas import PlaceRecord, RetrievalCase


def load_retrieval_cases(path) -> list[RetrievalCase]:
    data = read_json(path)
    return [RetrievalCase(**item) for item in data]


def normalize_region_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = normalize_text(value)
    return REGION_ALIASES.get(normalized, canonical_region(value))


def doc_id_from_metadata(metadata: dict[str, Any]) -> str:
    for key in ("place_id", "id", "source"):
        value = metadata.get(key)
        if value:
            return str(value)
    return ""


def _metadata_tags(metadata: dict[str, Any]) -> set[str]:
    raw_tags = metadata.get("tags") or ""
    if isinstance(raw_tags, str):
        return {normalize_text(tag.strip()) for tag in raw_tags.split(",") if tag.strip()}
    if isinstance(raw_tags, list):
        return {normalize_text(str(tag)) for tag in raw_tags if str(tag).strip()}
    return set()


def score_place_for_case(place: PlaceRecord, case: RetrievalCase) -> int:
    expected_region = normalize_region_name(case.expected_region)
    if expected_region and normalize_region_name(place.region) != expected_region:
        return 0

    required_tags = {normalize_text(tag) for tag in case.required_tags}
    optional_types = {normalize_text(value) for value in case.optional_types}
    place_tags = {normalize_text(tag) for tag in place.tags}
    place_type = normalize_text(place.place_type)

    tag_hits = len(required_tags & place_tags)
    type_hit = bool(optional_types and place_type in optional_types)

    if tag_hits >= 2 or (tag_hits >= 1 and type_hit):
        return 3
    if tag_hits >= 1 or type_hit:
        return 2
    return 1 if expected_region else 0


def score_metadata_for_case(
    metadata: dict[str, Any],
    case: RetrievalCase,
    place_by_id: dict[str, PlaceRecord] | None = None,
) -> int:
    doc_id = doc_id_from_metadata(metadata)
    if place_by_id and doc_id in place_by_id:
        return score_place_for_case(place_by_id[doc_id], case)

    expected_region = normalize_region_name(case.expected_region)
    metadata_region = normalize_region_name(str(metadata.get("region") or ""))
    if expected_region and metadata_region != expected_region:
        return 0

    required_tags = {normalize_text(tag) for tag in case.required_tags}
    optional_types = {normalize_text(value) for value in case.optional_types}
    metadata_tags = _metadata_tags(metadata)
    metadata_type = normalize_text(str(metadata.get("type") or ""))

    tag_hits = len(required_tags & metadata_tags)
    type_hit = bool(optional_types and metadata_type in optional_types)
    if tag_hits >= 2 or (tag_hits >= 1 and type_hit):
        return 3
    if tag_hits >= 1 or type_hit:
        return 2
    return 1 if expected_region else 0


def build_relevance_universe(
    case: RetrievalCase,
    places: list[PlaceRecord],
) -> tuple[set[str], dict[str, int]]:
    graded: dict[str, int] = {}

    for place in places:
        score = score_place_for_case(place, case)
        if score > 0:
            graded[place.id] = score

    relevant_ids = {place_id for place_id, score in graded.items() if score >= 2}
    if not relevant_ids:
        relevant_ids = set(graded)
    return relevant_ids, graded
