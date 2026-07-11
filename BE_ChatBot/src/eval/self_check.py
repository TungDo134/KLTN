from __future__ import annotations

from src.eval.common.config import EVAL_DIR, EXPECTED_TOTAL_PLACES
from src.eval.common.metrics import ndcg_at_k, precision_at_k, recall_at_k
from src.eval.common.place_loader import load_place_records
from src.eval.output.response_parser import parse_response_plan
from src.eval.output.validity import load_output_cases
from src.eval.retrieval.relevance import load_retrieval_cases


def run_self_check() -> None:
    places, warnings = load_place_records()
    if len(places) != EXPECTED_TOTAL_PLACES:
        raise AssertionError(
            f"Expected {EXPECTED_TOTAL_PLACES} places, found {len(places)}. Warnings: {warnings}"
        )

    retrieved = ["a", "b", "c"]
    relevant = {"a", "c", "d"}
    graded = {"a": 3, "b": 0, "c": 2, "d": 1}
    assert precision_at_k(retrieved, relevant, 3) == 2 / 3
    assert recall_at_k(retrieved, relevant, 3) == 2 / 3
    assert ndcg_at_k(retrieved, graded, 3) > 0

    sample = 'Answer text\n```json\n{"title":"Demo","region":"Da Nang","best_time":"morning","days":[]}\n```'
    parse_ok, parsed, error = parse_response_plan(sample)
    if not parse_ok or not parsed:
        raise AssertionError(f"Parser failed: {error}")

    retrieval_cases = load_retrieval_cases(
        EVAL_DIR / "retrieval" / "data" / "cases.json"
    )
    output_cases = load_output_cases(EVAL_DIR / "output" / "data" / "cases.json")
    if not retrieval_cases:
        raise AssertionError("No retrieval cases found.")
    if not output_cases:
        raise AssertionError("No output cases found.")

    print("Eval self-check passed. No LLM, Chroma, or reranker call was made.")


if __name__ == "__main__":
    run_self_check()
