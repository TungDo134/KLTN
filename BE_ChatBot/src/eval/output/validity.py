from __future__ import annotations

import argparse
import asyncio
import time
from collections import Counter
from pathlib import Path
from typing import Any

from src.eval.common.config import (
    CASE_DELAY_SECONDS,
    EVAL_DIR,
    OUTPUT_REQUIRED_DAY_FIELDS,
    OUTPUT_REQUIRED_PLACE_FIELDS,
    OUTPUT_REQUIRED_ROOT_FIELDS,
    llm_runtime_info,
)
from src.eval.common.metrics import average, latency_summary
from src.eval.common.path_utils import ensure_output_dir, format_float, format_percent, normalize_text, read_json, write_csv, write_json
from src.eval.common.place_loader import build_place_indexes, load_place_records
from src.eval.common.schemas import MetricRow, OutputCase, OutputValidityCaseResult
from src.eval.output.response_parser import parse_response_plan
from src.eval.retrieval.relevance import normalize_region_name


def load_output_cases(path) -> list[OutputCase]:
    data = read_json(path)
    return [OutputCase(**item) for item in data]


def _filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _required_field_completion(plan: dict[str, Any]) -> tuple[float, list[str]]:
    missing: list[str] = []
    total = 0
    filled = 0

    for field in OUTPUT_REQUIRED_ROOT_FIELDS:
        total += 1
        if _filled(plan.get(field)):
            filled += 1
        else:
            missing.append(field)

    days = plan.get("days") if isinstance(plan.get("days"), list) else []
    for day_index, day in enumerate(days, start=1):
        if not isinstance(day, dict):
            continue
        for field in OUTPUT_REQUIRED_DAY_FIELDS:
            total += 1
            if _filled(day.get(field)):
                filled += 1
            else:
                missing.append(f"days[{day_index}].{field}")

        places = day.get("places") if isinstance(day.get("places"), list) else []
        for place_index, place in enumerate(places, start=1):
            if not isinstance(place, dict):
                continue
            for field in OUTPUT_REQUIRED_PLACE_FIELDS:
                total += 1
                if _filled(place.get(field)):
                    filled += 1
                else:
                    missing.append(f"days[{day_index}].places[{place_index}].{field}")

    return (filled / total if total else 0.0), missing


def _place_names(plan: dict[str, Any]) -> list[str]:
    names: list[str] = []
    days = plan.get("days") if isinstance(plan.get("days"), list) else []
    for day in days:
        if not isinstance(day, dict):
            continue
        places = day.get("places") if isinstance(day.get("places"), list) else []
        for place in places:
            if isinstance(place, dict) and place.get("name"):
                names.append(str(place["name"]))
    return names


def _region_consistency(plan: dict[str, Any], case: OutputCase, place_by_name: dict[str, Any]) -> bool:
    expected_region = normalize_region_name(case.expected_region)
    plan_region = normalize_region_name(str(plan.get("region") or ""))
    if plan_region and expected_region and plan_region != expected_region:
        return False

    known_regions = []
    for name in _place_names(plan):
        place = place_by_name.get(normalize_text(name))
        if place:
            known_regions.append(normalize_region_name(place.canonical_region))

    return all(region == expected_region for region in known_regions)


def _schema_valid(plan: dict[str, Any]) -> bool:
    if not isinstance(plan.get("days"), list):
        return False
    for day in plan["days"]:
        if not isinstance(day, dict):
            return False
        if not isinstance(day.get("places"), list):
            return False
    return True


def validate_plan(plan: dict[str, Any], case: OutputCase, place_by_name: dict[str, Any]) -> tuple[bool, bool, float, bool, list[str]]:
    days = plan.get("days") if isinstance(plan.get("days"), list) else []
    day_count_match = len(days) == case.expected_days
    region_consistent = _region_consistency(plan, case, place_by_name)
    completion_rate, missing_fields = _required_field_completion(plan)

    normalized_names = [normalize_text(name) for name in _place_names(plan)]
    duplicates = [name for name, count in Counter(normalized_names).items() if name and count > 1]
    duplicate_place = bool(duplicates)

    return day_count_match, region_consistent, completion_rate, duplicate_place, missing_fields


async def benchmark_case(
    inference: Any,
    case: OutputCase,
    place_by_name: dict[str, Any],
    runtime_info: dict[str, str | None],
) -> OutputValidityCaseResult:
    started = time.perf_counter()
    try:
        response = await inference.predict_async(case.query, session_id=f"eval_{case.id}")
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return OutputValidityCaseResult(
            case_id=case.id,
            query=case.query,
            expected_region=case.expected_region,
            expected_days=case.expected_days,
            parse_success=False,
            schema_valid=False,
            day_count_match=False,
            region_consistent=False,
            duplicate_place=False,
            required_field_completion_rate=0.0,
            latency_ms=latency_ms,
            parse_error=f"predict_async failed: {type(exc).__name__}: {exc}",
            llm_runtime=runtime_info,
        )
    end_to_end_latency_ms = (time.perf_counter() - started) * 1000

    parse_ok, plan, parse_error = parse_response_plan(response)
    if not parse_ok or plan is None:
        return OutputValidityCaseResult(
            case_id=case.id,
            query=case.query,
            expected_region=case.expected_region,
            expected_days=case.expected_days,
            parse_success=False,
            schema_valid=False,
            day_count_match=False,
            region_consistent=False,
            duplicate_place=False,
            required_field_completion_rate=0.0,
            latency_ms=end_to_end_latency_ms,
            parse_error=parse_error or "Unknown parse error.",
            llm_runtime=runtime_info,
        )

    schema_valid = _schema_valid(plan)
    day_count_match, region_consistent, completion_rate, duplicate_place, missing_fields = validate_plan(plan, case, place_by_name)
    errors: list[str] = []
    if not schema_valid:
        errors.append("Plan JSON schema does not match expected structure.")
    if missing_fields:
        errors.append(f"Missing required fields: {', '.join(missing_fields[:20])}")
    if duplicate_place:
        errors.append("Duplicate place names found in plan.")

    return OutputValidityCaseResult(
        case_id=case.id,
        query=case.query,
        expected_region=case.expected_region,
        expected_days=case.expected_days,
        parse_success=True,
        schema_valid=schema_valid,
        day_count_match=day_count_match,
        region_consistent=region_consistent,
        duplicate_place=duplicate_place,
        required_field_completion_rate=completion_rate,
        latency_ms=end_to_end_latency_ms,
        parse_error="; ".join(errors) if errors else None,
        llm_runtime=runtime_info,
    )


def build_metric_rows(results: list[OutputValidityCaseResult]) -> list[MetricRow]:
    if not results:
        return []

    latency = latency_summary(item.latency_ms for item in results)
    return [
        MetricRow(
            group="Output Validity",
            metric_name="Day-count match rate",
            purpose="Kiem tra lich trinh co dung so ngay user yeu cau.",
            why_needed="Day la loi de thay voi user khi chatbot lap lich trinh sai so ngay.",
            formula="responses_with_correct_days / total_responses",
            unit="%",
            better_direction="Cao hon",
            data_source="Trip plan JSON tu RAGInference.predict_async",
            sample_size=str(len(results)),
            value=format_percent(average(1.0 if item.day_count_match else 0.0 for item in results)),
            note="Neu user hoi 3 ngay thi plan phai co dung 3 phan tu days.",
        ),
        MetricRow(
            group="Output Validity",
            metric_name="Region consistency rate",
            purpose="Kiem tra dia diem co dung vung user yeu cau.",
            why_needed="Tranh de xuat sai dia diem, vi du hoi Da Nang nhung tra ve Vung Tau.",
            formula="responses_all_places_in_expected_region / total_responses",
            unit="%",
            better_direction="Cao hon",
            data_source="Trip plan JSON + metadata place",
            sample_size=str(len(results)),
            value=format_percent(average(1.0 if item.region_consistent else 0.0 for item in results)),
            note="Chi doi chieu duoc voi place name co trong dataset.",
        ),
        MetricRow(
            group="Output Validity",
            metric_name="Required-field completion rate",
            purpose="Kiem tra tung item trong lich trinh co du thong tin bat buoc.",
            why_needed="Dam bao lich trinh hien thi day du title, time, place, tags.",
            formula="filled_required_fields / total_required_fields",
            unit="%",
            better_direction="Cao hon",
            data_source="Trip plan JSON",
            sample_size=str(len(results)),
            value=format_percent(average(item.required_field_completion_rate for item in results)),
            note="Field bat buoc bam theo output hien tai cua inference.py.",
        ),
        MetricRow(
            group="Output Validity",
            metric_name="End-to-end latency",
            purpose="Do thoi gian tra loi hoan chinh.",
            why_needed="Phan anh trai nghiem thuc te cua user khi qua ca RAG va LLM.",
            formula="elapsed_ms",
            unit="ms",
            better_direction="Thap hon",
            data_source="Timer quanh RAGInference.predict_async",
            sample_size=str(len(results)),
            value=(
                f"avg={format_float(latency['avg_ms'])}ms, "
                f"p95={format_float(latency['p95_ms'])}ms"
            ),
            note="Nen bao cao avg, min, max, p95 trong JSON output.",
        ),
    ]


async def sleep_between_cases(case_index: int, total_cases: int) -> None:
    if CASE_DELAY_SECONDS > 0 and case_index < total_cases - 1:
        await asyncio.sleep(CASE_DELAY_SECONDS)


async def run_output_validity(
    output_dir: Path | None = None,
    limit: int | None = None,
    case_id: str | None = None,
) -> tuple[dict[str, Any], list[MetricRow]]:
    # LLM note: this calls RAGInference.predict_async(), so it can use the
    # core answer LLM (LLM_PROVIDER/LLM_MODEL), the rewrite LLM
    # (REWRITE_LLM_PROVIDER/REWRITE_LLM_MODEL), and the configured reranker.
    from src.pipeline.inference import RAGInference

    output_dir = ensure_output_dir(output_dir)
    cases = load_output_cases(EVAL_DIR / "output" / "data" / "cases.json")
    if case_id:
        cases = [case for case in cases if case.id == case_id]
    if limit is not None:
        cases = cases[:limit]

    places, data_warnings = load_place_records()
    indexes = build_place_indexes(places)
    place_by_name = indexes["by_name"]

    inference = RAGInference()
    runtime_info = llm_runtime_info()
    results: list[OutputValidityCaseResult] = []
    for index, case in enumerate(cases):
        results.append(
            await benchmark_case(inference, case, place_by_name, runtime_info)
        )
        await sleep_between_cases(index, len(cases))

    rows = build_metric_rows(results)
    payload = {
        "llm_runtime": runtime_info,
        "case_delay_seconds": CASE_DELAY_SECONDS,
        "data_warnings": data_warnings,
        "case_count": len(results),
        "error_count": sum(1 for item in results if item.parse_error),
        "results": [item.to_dict() for item in results],
        "metrics": [row.to_report_row() for row in rows],
    }

    write_json(output_dir / "output_validity_results.json", payload)
    write_csv(output_dir / "output_validity_summary.csv", [row.to_report_row() for row in rows])
    return payload, rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run output validity benchmark.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case-id", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = ensure_output_dir(args.output_dir)
    asyncio.run(run_output_validity(output_dir, limit=args.limit, case_id=args.case_id))
    print(f"Output validity benchmark written to {output_dir}")


if __name__ == "__main__":
    main()
