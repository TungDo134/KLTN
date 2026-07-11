from __future__ import annotations

import os
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = EVAL_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

PLACE_DATA_DIR = SRC_DIR / "source_data" / "places_data"
OUTPUT_DIR = EVAL_DIR / "outputs"

EXPECTED_PLACE_FILES: dict[str, str] = {
    "dalat_100_tourist_spots.json": "Da Lat",
    "dn_100_tourist_spots.json": "Da Nang",
    "hcm_100_tourist_spots.json": "Ho Chi Minh",
    "hn_100_tourist_spots.json": "Ha Noi",
    "nt_100_tourist_spots.json": "Nha Trang",
    "vt_100_tourist_spots.json": "Vung Tau",
}
EXPECTED_PLACES_PER_REGION = 100
EXPECTED_TOTAL_PLACES = 600

COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "kltn_chatbot")
CHROMA_PERSIST_DIRECTORY = Path(
    os.getenv("PERSIST_DIRECTORY", str(PROJECT_ROOT / "src" / "db" / "chroma_db"))
)
if not CHROMA_PERSIST_DIRECTORY.is_absolute():
    CHROMA_PERSIST_DIRECTORY = PROJECT_ROOT / CHROMA_PERSIST_DIRECTORY

K_VALUES = (1, 3, 5)
TOP_K_RETRIEVE = 5
CASE_DELAY_SECONDS = float(os.getenv("EVAL_CASE_DELAY_SECONDS", "7"))

REQUIRED_PLACE_FIELDS = (
    "id",
    "name",
    "region",
    "type",
    "tags",
    "rating.score",
    "rating.review_count",
    "geo.lat",
    "geo.lng",
    "time.open",
    "time.close",
    "avg_duration_minutes",
    "entrance_fee",
    "description",
    "best_time",
)

OUTPUT_REQUIRED_ROOT_FIELDS = ("title", "region", "best_time", "days")
OUTPUT_REQUIRED_DAY_FIELDS = ("day", "title", "description", "places")
OUTPUT_REQUIRED_PLACE_FIELDS = ("name", "arrival", "departure", "tags")

REGION_ALIASES: dict[str, str] = {
    "da lat": "Da Lat",
    "dalat": "Da Lat",
    "da nang": "Da Nang",
    "danang": "Da Nang",
    "hcm": "Ho Chi Minh",
    "ho chi minh": "Ho Chi Minh",
    "tp hcm": "Ho Chi Minh",
    "sai gon": "Ho Chi Minh",
    "saigon": "Ho Chi Minh",
    "ha noi": "Ha Noi",
    "hanoi": "Ha Noi",
    "nha trang": "Nha Trang",
    "nhatrang": "Nha Trang",
    "vung tau": "Vung Tau",
    "vungtau": "Vung Tau",
}


def llm_runtime_info() -> dict[str, str | None]:
    """Return non-secret LLM/reranker settings for benchmark reports."""

    reranker_provider = (os.getenv("RERANKER_PROVIDER") or "huggingface").strip().lower()
    explicit_reranker_model = os.getenv("RERANKER_MODEL_NAME")
    reranker_model = (
        explicit_reranker_model.strip()
        if explicit_reranker_model and explicit_reranker_model.strip()
        else ("rerank-v3.5" if reranker_provider == "cohere" else "BAAI/bge-reranker-v2-m3")
    )

    return {
        "core_llm_provider": os.getenv("LLM_PROVIDER"),
        "core_llm_model": os.getenv("LLM_MODEL"),
        "rewrite_llm_provider": os.getenv("REWRITE_LLM_PROVIDER"),
        "rewrite_llm_model": os.getenv("REWRITE_LLM_MODEL"),
        "reranker_provider": reranker_provider,
        "reranker_model": reranker_model,
        "reranker_top_n": os.getenv("RERANKER_TOP_N", "20"),
        "eval_case_delay_seconds": str(CASE_DELAY_SECONDS),
        "chroma_collection": COLLECTION_NAME,
        "chroma_persist_directory": str(CHROMA_PERSIST_DIRECTORY),
    }
