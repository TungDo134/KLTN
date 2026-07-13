from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.eval.common.path_utils import ensure_output_dir
from src.eval.dataset.coverage import run_dataset_coverage
from src.eval.output.validity import run_output_validity
from src.eval.reporting.report_builder import build_report
from src.eval.retrieval.benchmark import run_retrieval_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all eval benchmarks.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None, help="Limit retrieval/output cases for smoke runs.")
    parser.add_argument("--skip-retrieval", action="store_true")
    parser.add_argument("--skip-output", action="store_true")
    return parser.parse_args()


async def run_all(output_dir: Path | None = None, limit: int | None = None, skip_retrieval: bool = False, skip_output: bool = False) -> None:
    output_dir = ensure_output_dir(output_dir)
    run_dataset_coverage(output_dir)

    # LLM note: retrieval can call the rewrite LLM via MultiQueryRetriever and
    # the configured reranker provider/model.
    if not skip_retrieval:
        await run_retrieval_benchmark(output_dir, limit=limit)

    # LLM note: output validity calls RAGInference.predict_async(), which can
    # call the core answer LLM plus the rewrite LLM and reranker.
    if not skip_output:
        await run_output_validity(output_dir, limit=limit)

    build_report(output_dir)


def main() -> None:
    args = parse_args()
    asyncio.run(
        run_all(
            output_dir=args.output_dir,
            limit=args.limit,
            skip_retrieval=args.skip_retrieval,
            skip_output=args.skip_output,
        )
    )
    print(f"Eval outputs written to {ensure_output_dir(args.output_dir)}")


if __name__ == "__main__":
    main()
