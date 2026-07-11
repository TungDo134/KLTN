from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from src.eval.common.config import (
    CASE_DELAY_SECONDS,
    EVAL_DIR,
    K_VALUES,
    TOP_K_RETRIEVE,
    llm_runtime_info,
)
from src.eval.common.metrics import (
    average,
    latency_summary,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from src.eval.common.path_utils import (
    ensure_output_dir,
    format_float,
    format_percent,
    write_csv,
    write_json,
)
from src.eval.common.place_loader import build_place_indexes, load_place_records
from src.eval.common.schemas import MetricRow, RetrievalCase, RetrievalCaseResult
from src.eval.retrieval.relevance import (
    build_relevance_universe,
    doc_id_from_metadata,
    load_retrieval_cases,
    score_metadata_for_case,
)


def _doc_ids(docs: list[Document]) -> list[str]:
    return [doc_id_from_metadata(doc.metadata) for doc in docs]


def _graded_with_retrieved_docs(
    docs: list[Document],
    case: RetrievalCase,
    place_by_id: dict[str, Any],
    graded_relevance: dict[str, int],
) -> dict[str, int]:
    merged = dict(graded_relevance)
    for doc in docs:
        doc_id = doc_id_from_metadata(doc.metadata)
        if doc_id and doc_id not in merged:
            merged[doc_id] = score_metadata_for_case(doc.metadata, case, place_by_id)
    return merged


async def benchmark_case(
    case: RetrievalCase,
    retriever: Any,
    reranker: Any,
    place_by_id: dict[str, Any],
    relevant_ids: set[str],
    graded_relevance: dict[str, int],
    runtime_info: dict[str, str | None],
) -> RetrievalCaseResult:
    started = time.perf_counter()
    raw_docs = await retriever.ainvoke(case.query)
    retrieval_latency_ms = (time.perf_counter() - started) * 1000

    rerank_started = time.perf_counter()
    rerank_error: str | None = None
    try:
        reranked_docs = reranker.compress_documents(raw_docs, case.query)
    except Exception as exc:
        rerank_error = f"{type(exc).__name__}: {exc}"
        reranked_docs = raw_docs
    rerank_latency_ms = (time.perf_counter() - rerank_started) * 1000

    raw_top_docs = list(raw_docs)[:TOP_K_RETRIEVE]
    reranked_top_docs = list(reranked_docs)[:TOP_K_RETRIEVE]

    before_ids = _doc_ids(raw_top_docs)
    after_ids = _doc_ids(reranked_top_docs)
    scored_docs = list(raw_top_docs) + list(reranked_top_docs)
    graded_for_case = _graded_with_retrieved_docs(
        scored_docs, case, place_by_id, graded_relevance
    )

    metrics_before: dict[str, float] = {}
    metrics_after: dict[str, float] = {}
    for k in K_VALUES:
        metrics_before[f"precision@{k}"] = precision_at_k(before_ids, relevant_ids, k)
        metrics_after[f"precision@{k}"] = precision_at_k(after_ids, relevant_ids, k)

    metrics_before[f"recall@{TOP_K_RETRIEVE}"] = recall_at_k(
        before_ids, relevant_ids, TOP_K_RETRIEVE
    )
    metrics_after[f"recall@{TOP_K_RETRIEVE}"] = recall_at_k(
        after_ids, relevant_ids, TOP_K_RETRIEVE
    )
    metrics_before[f"ndcg@{TOP_K_RETRIEVE}"] = ndcg_at_k(
        before_ids, graded_for_case, TOP_K_RETRIEVE
    )
    metrics_after[f"ndcg@{TOP_K_RETRIEVE}"] = ndcg_at_k(
        after_ids, graded_for_case, TOP_K_RETRIEVE
    )

    return RetrievalCaseResult(
        case_id=case.id,
        query=case.query,
        expected_region=case.expected_region,
        relevant_universe_size=len(relevant_ids),
        raw_doc_ids=before_ids,
        reranked_doc_ids=after_ids,
        metrics_before_rerank=metrics_before,
        metrics_after_rerank=metrics_after,
        retrieval_latency_ms=retrieval_latency_ms,
        rerank_latency_ms=rerank_latency_ms,
        llm_runtime=runtime_info,
        rerank_error=rerank_error,
    )


async def sleep_between_cases(case_index: int, total_cases: int) -> None:
    if CASE_DELAY_SECONDS > 0 and case_index < total_cases - 1:
        await asyncio.sleep(CASE_DELAY_SECONDS)


def build_metric_rows(results: list[RetrievalCaseResult]) -> list[MetricRow]:
    if not results:
        return []

    p5_before = average(
        item.metrics_before_rerank.get("precision@5", 0.0) for item in results
    )
    p5_after = average(
        item.metrics_after_rerank.get("precision@5", 0.0) for item in results
    )
    ndcg_before = average(
        item.metrics_before_rerank.get("ndcg@5", 0.0) for item in results
    )
    ndcg_after = average(
        item.metrics_after_rerank.get("ndcg@5", 0.0) for item in results
    )
    retrieval_latency = latency_summary(item.retrieval_latency_ms for item in results)
    rerank_latency = latency_summary(item.rerank_latency_ms for item in results)
    rerank_error_count = sum(1 for item in results if item.rerank_error)

    return [
        MetricRow(
            group="Retrieval Quality",
            metric_name="Precision@K",
            purpose="Do ty le tai lieu dung trong top-K.",
            why_needed="Day la chi so quan trong nhat de biet retrieval co dua dung dia diem len dau khong.",
            formula="relevant_docs_in_top_k / k",
            unit="%",
            better_direction="Cao hon",
            data_source="Ground truth tu src/eval/retrieval/data/cases.json + ket qua retriever",
            sample_size=str(len(results)),
            value=", ".join(
                f"P@{k}={format_percent(average(item.metrics_after_rerank.get(f'precision@{k}', 0.0) for item in results))}"
                for k in K_VALUES
            ),
            note="Nen bao cao K = 1, 3, 5. Gia tri nay tinh sau rerank.",
        ),
        MetricRow(
            group="Retrieval Quality",
            metric_name="Recall@K",
            purpose="Do kha nang tim du tai lieu lien quan trong top-K.",
            why_needed="Precision cao chua chac da tim du cac dia diem phu hop cho lap lich trinh.",
            formula="relevant_docs_in_top_k / total_relevant_docs",
            unit="%",
            better_direction="Cao hon",
            data_source="Ground truth tu src/eval/retrieval/data/cases.json + ket qua retriever",
            sample_size=str(len(results)),
            value=format_percent(
                average(
                    item.metrics_after_rerank.get("recall@5", 0.0) for item in results
                )
            ),
            note="Mac dinh dung Recall@5 de khop top-K dang lay.",
        ),
        MetricRow(
            group="Retrieval Quality",
            metric_name="nDCG@K",
            purpose="Do chat luong thu hang cua tai lieu lien quan.",
            why_needed="Tai lieu dung nam rank cao tot hon tai lieu dung nam cuoi danh sach.",
            formula="DCG@K / IDCG@K",
            unit="%",
            better_direction="Cao hon",
            data_source="Ground truth co relevance score tu rule theo region/tag/type",
            sample_size=str(len(results)),
            value=format_percent(
                average(
                    item.metrics_after_rerank.get("ndcg@5", 0.0) for item in results
                )
            ),
            note="Phu hop khi ground truth co muc do lien quan 1-3.",
        ),
        MetricRow(
            group="Retrieval Quality",
            metric_name="Retrieval latency",
            purpose="Do thoi gian truy xuat va rerank.",
            why_needed="Cho biet chi phi cua buoc RAG truoc khi goi LLM sinh cau tra loi.",
            formula="elapsed_ms",
            unit="ms",
            better_direction="Thap hon",
            data_source="Timer trong benchmark retrieval",
            sample_size=str(len(results)),
            value=(
                f"retrieval avg={format_float(retrieval_latency['avg_ms'])}ms, "
                f"rerank avg={format_float(rerank_latency['avg_ms'])}ms"
            ),
            note="Nen bao cao avg, min, max, p95 trong JSON output.",
        ),
        MetricRow(
            group="Retrieval Quality",
            metric_name="Rerank improvement",
            purpose="So sanh truoc/sau rerank.",
            why_needed="Chung minh reranker co tac dung cai thien thu hang hay khong.",
            formula="metric_after_rerank - metric_before_rerank",
            unit="diem %",
            better_direction="Cao hon",
            data_source="Retriever output truoc/sau DocumentReranker",
            sample_size=str(len(results)),
            value=(
                f"Delta P@5={format_percent(p5_after - p5_before)}, "
                f"Delta nDCG@5={format_percent(ndcg_after - ndcg_before)}"
            ),
            note=(
                "Gia tri am nghia la rerank lam ket qua xau hon voi bo case hien tai. "
                f"Rerank failed cases: {rerank_error_count}/{len(results)}."
            ),
        ),
    ]


async def run_retrieval_benchmark(
    output_dir: Path | None = None,
    limit: int | None = None,
    case_id: str | None = None,
) -> tuple[dict[str, Any], list[MetricRow]]:
    # LLM note: RAGStorage.get_multi_query_retriever() may call the rewrite LLM
    # through MultiQueryRetriever. Record REWRITE_LLM_PROVIDER/REWRITE_LLM_MODEL
    # in the output so benchmark runs can be compared fairly.
    from src.pipeline.rag_pipline import RAGStorage

    output_dir = ensure_output_dir(output_dir)
    cases = load_retrieval_cases(EVAL_DIR / "retrieval" / "data" / "cases.json")
    if case_id:
        cases = [case for case in cases if case.id == case_id]
    if limit is not None:
        cases = cases[:limit]

    places, data_warnings = load_place_records()
    indexes = build_place_indexes(places)
    place_by_id = indexes["by_id"]

    storage = RAGStorage()
    retriever, reranker = storage.get_multi_query_retriever()
    runtime_info = llm_runtime_info()

    results: list[RetrievalCaseResult] = []
    for index, case in enumerate(cases):
        relevant_ids, graded = build_relevance_universe(case, places)
        result = await benchmark_case(
            case=case,
            retriever=retriever,
            reranker=reranker,
            place_by_id=place_by_id,
            relevant_ids=relevant_ids,
            graded_relevance=graded,
            runtime_info=runtime_info,
        )
        results.append(result)
        await sleep_between_cases(index, len(cases))

    rows = build_metric_rows(results)
    payload = {
        "llm_runtime": runtime_info,
        "case_delay_seconds": CASE_DELAY_SECONDS,
        "data_warnings": data_warnings,
        "case_count": len(results),
        "rerank_error_count": sum(1 for item in results if item.rerank_error),
        "results": [item.to_dict() for item in results],
        "metrics": [row.to_report_row() for row in rows],
    }

    write_json(output_dir / "retrieval_results.json", payload)
    write_csv(
        output_dir / "retrieval_summary.csv", [row.to_report_row() for row in rows]
    )
    return payload, rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retrieval benchmark.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case-id", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = ensure_output_dir(args.output_dir)
    asyncio.run(
        run_retrieval_benchmark(output_dir, limit=args.limit, case_id=args.case_id)
    )
    print(f"Retrieval benchmark written to {output_dir}")


if __name__ == "__main__":
    main()
