"""
config.py
==== KHI IMPLEMENET CHECK KĨ CÁC PATH TRƯỚC ===
Cấu hình chung cho toàn bộ CRAWL_DATA_CHATBOT pipeline.
Load từ .env hoặc hardcode default.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── ChromaDB (phải trỏ đúng vào BE_ChatBot/db/) ──────────────────────
CHROMA_PERSIST_DIR = os.getenv("PERSIST_DIRECTORY", "../BE_ChatBot/db/")
CHROMA_COLLECTION = "kltn_chatbot"

# ── Embedding ─────────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "AITeamVN/Vietnamese_Embedding")
EMBEDDING_CACHE_DIR = os.getenv("CACHE_FOLDER", "../BE_ChatBot/src/model/embeddings")

# ── Crawler ───────────────────────────────────────────────────────────
REQUEST_DELAY_SEC = 2  # delay giữa các request để tránh bị block
MAX_RETRIES = 3
REQUEST_TIMEOUT_SEC = 10

# ── Data paths ────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "places")

# ── Regions được hỗ trợ ───────────────────────────────────────────────
SUPPORTED_REGIONS = ["dalat", "hanoi", "hcmc", "danang"]

# ── budget_level mapping (dựa trên giá vé người lớn, VND) ────────────
BUDGET_LEVEL_THRESHOLDS = {
    "free": 0,
    "low": 100_000,
    "medium": 300_000,
    "high": float("inf"),
}
