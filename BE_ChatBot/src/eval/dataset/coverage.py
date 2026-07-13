from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.eval.common.config import EXPECTED_PLACES_PER_REGION, EXPECTED_TOTAL_PLACES, REQUIRED_PLACE_FIELDS
from src.eval.common.path_utils import ensure_output_dir, format_float, format_percent, normalize_text, write_csv, write_json
from src.eval.common.place_loader import get_nested, is_missing, load_place_records
from src.eval.common.schemas import DatasetCoverageResult, MetricRow


def _missing_field_rates(raw_places: list[dict[str, Any]]) -> dict[str, float]:
    total = len(raw_places)
    if not total:
        return {field: 0.0 for field in REQUIRED_PLACE_FIELDS}

    missing_by_field: dict[str, float] = {}
    for field in REQUIRED_PLACE_FIELDS:
        count = sum(1 for place in raw_places if is_missing(get_nested(place, field)))
        missing_by_field[field] = count / total

    return missing_by_field


def _average_rating_by_region(raw_places: list[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for place in raw_places:
        region = str(place.get("region") or "Unknown")
        score = get_nested(place, "rating.score")
        if isinstance(score, (int, float)):
            buckets[region].append(float(score))

    return {
        region: round(sum(values) / len(values), 3)
        for region, values in sorted(buckets.items())
        if values
    }


def build_dataset_coverage() -> DatasetCoverageResult:
    places, warnings = load_place_records()
    raw_places = [place.raw for place in places]

    region_counts = Counter(place.canonical_region for place in places)
    unique_tags = sorted({tag for place in places for tag in place.tags})
    unique_types = sorted({place.place_type for place in places if place.place_type})
    missing_by_field = _missing_field_rates(raw_places)
    avg_rating_by_region = _average_rating_by_region(raw_places)

    if len(places) != EXPECTED_TOTAL_PLACES:
        warnings.append(f"Expected {EXPECTED_TOTAL_PLACES} places, found {len(places)}.")
    for region, count in sorted(region_counts.items()):
        if count != EXPECTED_PLACES_PER_REGION:
            warnings.append(f"{region}: expected {EXPECTED_PLACES_PER_REGION}, found {count}.")
    name_counts = Counter(normalize_text(place.name) for place in places if place.name)
    duplicated_names = [name for name, count in name_counts.items() if count > 1]
    if duplicated_names:
        warnings.append(f"Duplicated normalized names: {len(duplicated_names)}.")

    return DatasetCoverageResult(
        total_places=len(places),
        places_by_region=dict(sorted(region_counts.items())),
        unique_tags_count=len(unique_tags),
        unique_types_count=len(unique_types),
        missing_metadata_rate_by_field=missing_by_field,
        avg_rating_by_region=avg_rating_by_region,
        warnings=warnings,
    )


def build_metric_rows(result: DatasetCoverageResult) -> list[MetricRow]:
    missing_rate = (
        sum(result.missing_metadata_rate_by_field.values()) / len(result.missing_metadata_rate_by_field)
        if result.missing_metadata_rate_by_field
        else 0.0
    )
    region_counts = ", ".join(f"{region}: {count}" for region, count in result.places_by_region.items())
    ratings = ", ".join(
        f"{region}: {format_float(value)}" for region, value in result.avg_rating_by_region.items()
    )

    return [
        MetricRow(
            group="Dataset Coverage",
            metric_name="Tong so dia diem",
            purpose="Cho biet quy mo du lieu dang dung.",
            why_needed="Chung minh benchmark duoc chay tren tap 600 dia diem, 100 dia diem moi vung.",
            formula="count(place)",
            unit="dia diem",
            better_direction="Khong ap dung",
            data_source="src/source_data/places_data/*.json",
            sample_size=str(result.total_places),
            value=result.total_places,
            note="Nen bao cao tong va chi tiet theo vung.",
        ),
        MetricRow(
            group="Dataset Coverage",
            metric_name="So dia diem theo vung",
            purpose="Kiem tra do can bang cua 6 tap dia diem.",
            why_needed="Neu moi vung deu co 100 dia diem thi benchmark truy xuat theo vung cong bang hon.",
            formula="count(place by region)",
            unit="dia diem/vung",
            better_direction="Gan 100 moi vung",
            data_source="src/source_data/places_data/*.json",
            sample_size=str(result.total_places),
            value=region_counts,
            note="Ky vong: 100 dia diem/vung.",
        ),
        MetricRow(
            group="Dataset Coverage",
            metric_name="So tag/type duy nhat",
            purpose="Do do da dang nhu cau du lich ma metadata co the mo ta.",
            why_needed="Tag/type phong phu giup giai thich kha nang loc va de xuat cua he thong.",
            formula="unique(tags), unique(type)",
            unit="so luong",
            better_direction="Cao hon",
            data_source="Place JSON metadata",
            sample_size=str(result.total_places),
            value=f"{result.unique_tags_count} tags, {result.unique_types_count} types",
            note="Nen dinh kem danh sach top tags neu can phan tich sau.",
        ),
        MetricRow(
            group="Dataset Coverage",
            metric_name="Ty le thieu metadata",
            purpose="Kiem tra chat luong du lieu dau vao.",
            why_needed="Metadata thieu co the lam yeu loc, rerank va lap lich trinh.",
            formula="avg(missing_field_count / total_places by required field)",
            unit="%",
            better_direction="Thap hon",
            data_source="Place JSON metadata",
            sample_size=str(result.total_places),
            value=format_percent(missing_rate),
            note="Nen bao cao them missing theo tung field trong JSON output.",
        ),
        MetricRow(
            group="Dataset Coverage",
            metric_name="Rating trung binh theo vung",
            purpose="Mo ta chat luong danh gia cua dia diem trong moi vung.",
            why_needed="Giup giai thich khi recommender uu tien dia diem co rating cao.",
            formula="avg(rating.score by region)",
            unit="diem",
            better_direction="Cao hon",
            data_source="Place JSON rating.score",
            sample_size=str(result.total_places),
            value=ratings,
            note="Chi tinh cac item co rating.score hop le.",
        ),
    ]


def run_dataset_coverage(output_dir: Path | None = None) -> tuple[dict[str, Any], list[MetricRow]]:
    output_dir = ensure_output_dir(output_dir)
    result = build_dataset_coverage()
    rows = build_metric_rows(result)
    payload = {
        "summary": result.__dict__,
        "metrics": [row.to_report_row() for row in rows],
    }

    write_json(output_dir / "dataset_coverage.json", payload)
    write_csv(output_dir / "dataset_coverage_summary.csv", [row.to_report_row() for row in rows])
    return payload, rows


def main() -> None:
    output_dir = ensure_output_dir()
    run_dataset_coverage(output_dir)
    print(f"Dataset coverage written to {output_dir}")


if __name__ == "__main__":
    main()
