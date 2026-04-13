"""
pipeline.py
Master script — chạy toàn bộ: Crawl → Validate → Ingest.
Đây là file duy nhất cần gọi từ command line.

Usage:
  python pipeline.py --region dalat
  python pipeline.py --region all
  python pipeline.py --skip-crawl   # chỉ validate + ingest data có sẵn trong data/
  python pipeline.py --skip-ingest  # chỉ crawl + validate, chưa đưa vào ChromaDB
"""

import argparse
from crawlers.tripadvisor_crawler import TripAdvisorCrawler
from crawlers.foursquare_crawler import FoursquareCrawler
from validators.schema_validator import SchemaValidator
from ingest.json_to_chromadb import JSONToChromaDB
from config import SUPPORTED_REGIONS, DATA_DIR


def run_pipeline(region: str, skip_crawl: bool = False, skip_ingest: bool = False):
    """
    Pseudo:

    print(f"▶ Starting pipeline for region: {region}")

    # ── Bước 1: Crawl ──────────────────────────────────────────────
    if not skip_crawl:
      raw_places = []
      for CrawlerClass in [TripAdvisorCrawler, FoursquareCrawler]:
        crawler    = CrawlerClass(region)
        raw        = crawler.crawl()
        raw_places.extend(raw)
        crawler.save_raw(raw, f"{DATA_DIR}/{region}_raw_{source}.json")

      print(f"  Crawled {len(raw_places)} raw places")
    else:
      raw_places = _load_existing_json(region)
      print(f"  Loaded {len(raw_places)} places from existing JSON")

    # ── Bước 2: Validate ───────────────────────────────────────────
    validator = SchemaValidator()
    valid, invalid = validator.validate_all(raw_places)
    print(f"  Valid: {len(valid)} | Invalid: {len(invalid)}")

    if invalid:
      validator.log_invalid(invalid, f"{DATA_DIR}/{region}_invalid.json")

    # ── Bước 3: Save valid JSON ────────────────────────────────────
    _save_json(valid, f"{DATA_DIR}/{region}.json")
    print(f"  Saved {len(valid)} valid places → {DATA_DIR}/{region}.json")

    # ── Bước 4: Ingest vào ChromaDB ────────────────────────────────
    if not skip_ingest:
      ingester = JSONToChromaDB()
      summary  = ingester.ingest_file(f"{DATA_DIR}/{region}.json")
      print(f"  ChromaDB upsert: {summary}")

    print(f"✅ Pipeline complete for [{region}]")
    """
    # TODO: implement
    pass


def main():
    """
    Pseudo:
      parser = argparse.ArgumentParser()
      parser.add_argument("--region",       default="all", choices=SUPPORTED_REGIONS + ["all"])
      parser.add_argument("--skip-crawl",   action="store_true")
      parser.add_argument("--skip-ingest",  action="store_true")
      args = parser.parse_args()

      regions = SUPPORTED_REGIONS if args.region == "all" else [args.region]
      for region in regions:
        run_pipeline(region, args.skip_crawl, args.skip_ingest)
    """
    # TODO: implement
    from pathlib import Path

    print(f"Hello Im'from {Path(__file__).resolve()}")
    pass


if __name__ == "__main__":
    main()
