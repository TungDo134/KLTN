"""Manual integration test for Gemini Embedding 1 with the current RAG data."""

from __future__ import annotations

import hashlib
import os
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_DATA_DIR = PROJECT_ROOT / "src" / "source_data" / "places_data"
MODEL_NAME = "models/gemini-embedding-001"
COLLECTION_NAME = "test_gemini_embedding"
PERSIST_DIRECTORY = Path(__file__).resolve().parent / COLLECTION_NAME
BATCH_SIZE = 100
BATCH_DELAY_SECONDS = 65
MAX_RATE_LIMIT_RETRIES = 3

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def build_vector_store(chunks, embedding_model) -> Chroma:
    if not chunks:
        raise ValueError("No chunks found to embed.")

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
        persist_directory=str(PERSIST_DIRECTORY),
        collection_metadata={"hnsw:space": "cosine"},
    )

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        batch_number = start // BATCH_SIZE + 1

        if batch_number > 1:
            print(
                f"Waiting {BATCH_DELAY_SECONDS}s before batch {batch_number} "
                "to respect the free-tier rate limit..."
            )
            time.sleep(BATCH_DELAY_SECONDS)

        rate_limit_retries = 0
        while True:
            try:
                vectorstore.add_documents(batch)
                print(f"Batch {batch_number}: OK ({len(batch)} chunks)")
                break
            except Exception as exc:
                error_message = str(exc)
                is_rate_limit_error = (
                    "429" in error_message or "RESOURCE_EXHAUSTED" in error_message
                )

                if not is_rate_limit_error:
                    raise RuntimeError(
                        f"Batch {batch_number} failed: {type(exc).__name__}: {exc}"
                    ) from exc

                rate_limit_retries += 1
                if rate_limit_retries > MAX_RATE_LIMIT_RETRIES:
                    raise RuntimeError(
                        f"Batch {batch_number} still rate limited after "
                        f"{MAX_RATE_LIMIT_RETRIES} retries: {exc}"
                    ) from exc

                print(
                    f"Batch {batch_number}: rate limited (429). "
                    f"Waiting {BATCH_DELAY_SECONDS}s before retry "
                    f"{rate_limit_retries}/{MAX_RATE_LIMIT_RETRIES}..."
                )
                time.sleep(BATCH_DELAY_SECONDS)

    return vectorstore


def content_checksum(items) -> str:
    rows = sorted(
        f"{item.metadata.get('place_id', '')}\0{item.page_content}" for item in items
    )
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def stored_content_checksum(metadatas, contents) -> str:
    rows = sorted(
        f"{metadata.get('place_id', '')}\0{content}"
        for metadata, content in zip(metadatas, contents)
    )
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def print_region_coverage(documents, chunks, stored_metadatas) -> bool:
    document_regions = Counter(doc.metadata.get("region", "UNKNOWN") for doc in documents)
    chunk_regions = Counter(chunk.metadata.get("region", "UNKNOWN") for chunk in chunks)
    stored_regions = Counter(metadata.get("region", "UNKNOWN") for metadata in stored_metadatas)

    print("\nCoverage by region:")
    print(f"{'Region':<20} {'Documents':>10} {'Chunks':>10} {'Stored':>10}")
    for region in sorted(set(document_regions) | set(chunk_regions) | set(stored_regions)):
        print(
            f"{region:<20} {document_regions[region]:>10} "
            f"{chunk_regions[region]:>10} {stored_regions[region]:>10}"
        )

    return chunk_regions == stored_regions


def run_test() -> bool:
    print("=" * 60)
    print("GEMINI EMBEDDING 1 COMPATIBILITY TEST")
    print("=" * 60)
    print(f"Model      : {MODEL_NAME}")
    print(f"Collection : {COLLECTION_NAME}")
    print(f"Database   : {PERSIST_DIRECTORY}")

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("NOT SUITABLE: GEMINI_API_KEY or GOOGLE_API_KEY is not set.")
        return False

    if PERSIST_DIRECTORY.exists():
        print(
            "NOT SUITABLE: database directory already exists. "
            "Delete it manually before running a fresh test."
        )
        return False

    vectorstore = None
    try:
        from src.pipeline.rag_pipline import load_json_places, split_documents

        documents = load_json_places(str(JSON_DATA_DIR))
        chunks = split_documents(documents, chunk_size=1000, chunk_overlap=150)

        print(f"Documents  : {len(documents)}")
        print(f"Chunks     : {len(chunks)}")

        embedding_model = GoogleGenerativeAIEmbeddings(model=MODEL_NAME)

        started_at = time.perf_counter()
        vectorstore = build_vector_store(chunks, embedding_model)
        embedding_seconds = time.perf_counter() - started_at

        sample = vectorstore.get(limit=1, include=["embeddings"])
        stored = vectorstore.get(include=["metadatas", "documents"])
        embeddings = sample.get("embeddings")
        stored_metadatas = stored.get("metadatas") or []
        stored_contents = stored.get("documents") or []

        if embeddings is None or len(embeddings) == 0:
            raise RuntimeError("ChromaDB did not return a stored embedding.")

        document_ids = [doc.metadata.get("place_id") for doc in documents]
        chunk_ids = [chunk.metadata.get("place_id") for chunk in chunks]
        stored_ids = [metadata.get("place_id") for metadata in stored_metadatas]
        document_id_set = {place_id for place_id in document_ids if place_id}
        chunk_id_set = {place_id for place_id in chunk_ids if place_id}
        stored_id_set = {place_id for place_id in stored_ids if place_id}

        missing_ids = chunk_id_set - stored_id_set
        unexpected_ids = stored_id_set - chunk_id_set
        missing_chunk_metadata = sum(place_id is None for place_id in chunk_ids)
        missing_stored_metadata = sum(place_id is None for place_id in stored_ids)
        empty_chunks = sum(not chunk.page_content.strip() for chunk in chunks)
        empty_stored_contents = sum(not content.strip() for content in stored_contents)
        expected_checksum = content_checksum(chunks)
        actual_checksum = stored_content_checksum(stored_metadatas, stored_contents)
        region_coverage_matches = print_region_coverage(
            documents, chunks, stored_metadatas
        )

        checks = {
            "stored_count": len(stored.get("ids") or []) == len(chunks),
            "document_ids_reach_chunks": document_id_set == chunk_id_set,
            "stored_place_ids": chunk_id_set == stored_id_set,
            "metadata_complete": missing_chunk_metadata == 0
            and missing_stored_metadata == 0,
            "content_complete": empty_chunks == 0
            and empty_stored_contents == 0
            and expected_checksum == actual_checksum,
            "region_coverage": region_coverage_matches,
        }

        print("\n" + "-" * 60)
        print(f"JSON files             : {len(list(JSON_DATA_DIR.glob('*.json')))}")
        print(f"Documents              : {len(documents)}")
        print(f"Unique document IDs    : {len(document_id_set)}")
        print(f"Chunks expected/stored : {len(chunks)}/{len(stored.get('ids') or [])}")
        print(f"Unique stored IDs      : {len(stored_id_set)}")
        print(f"Missing IDs            : {len(missing_ids)}")
        print(f"Unexpected IDs         : {len(unexpected_ids)}")
        print(f"Missing place_id       : {missing_chunk_metadata + missing_stored_metadata}")
        print(f"Empty content          : {empty_chunks + empty_stored_contents}")
        print(f"Content checksum       : {actual_checksum}")
        print(f"Checksum matches       : {'YES' if expected_checksum == actual_checksum else 'NO'}")
        print(f"Vector dimension       : {len(embeddings[0])}")
        print(f"Embedding time         : {embedding_seconds:.2f}s")

        for check_name, passed in checks.items():
            print(f"Check {check_name:<24}: {'PASS' if passed else 'FAIL'}")

        if not all(checks.values()):
            raise RuntimeError("Data completeness verification failed.")

        print(f"ChromaDB retained at: {PERSIST_DIRECTORY}")
        print("SUITABLE: all current RAG chunks were embedded and stored successfully.")
        return True
    except Exception as exc:
        print(f"NOT SUITABLE: {type(exc).__name__}: {exc}")
        print(f"ChromaDB retained for inspection at: {PERSIST_DIRECTORY}")
        return False
    finally:
        if vectorstore is not None:
            client = getattr(vectorstore, "_client", None)
            if client is not None and hasattr(client, "close"):
                client.close()
            vectorstore = None


def main() -> None:
    raise SystemExit(0 if run_test() else 1)


if __name__ == "__main__":
    main()
