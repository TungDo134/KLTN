# ============================================================
# ĐÂY LÀ FILE DUY NHẤT CẦN SỬA KHI THAY DATA MỚI
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

# eval/ → BE_ChatBot/src/eval/ → lên 2 tầng = BE_ChatBot/src/ → lên 1 tầng nữa = BE_ChatBot/
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # BE_ChatBot/src/eval/
_PROJECT_ROOT = os.path.normpath(os.path.join(_BASE_DIR, "../.."))  # BE_ChatBot/  ← 2 tầng

_raw = os.getenv("PERSIST_DIRECTORY", "src/db/chroma_db")
PERSIST_DIRECTORY = (
    _raw if os.path.isabs(_raw)
    else os.path.normpath(os.path.join(_PROJECT_ROOT, _raw))
)

GROUND_TRUTH_PATH = "eval/ground_truth.json"

# --- ChromaDB collection ---
COLLECTION_NAME = "kltn_chatbot"

# --- Evaluation ---
K_VALUES = [1, 3, 5, 10]  # Precision@K và nDCG@K sẽ tính cho tất cả K này
TOP_K_RETRIEVE = 5  # số docs ChromaDB trả về tối đa (>= max(K_VALUES))

# --- Doc ID key ---
# Cách tạo unique ID cho mỗi chunk từ metadata.
# Hiện tại: "source::page" vì data là PDF/txt không có doc_id riêng.
# Khi đổi sang data du lịch có field "place_id": đổi thành lambda m: m["place_id"]
DOC_ID_FN = lambda metadata: f"{metadata.get('source', '')}::page{metadata.get('page', 0)}"

# --- LLM cho ground truth generation ---
GROQ_MODEL = "llama-3.1-8b-instant"

# --- Domain context (để LLM hiểu domain khi generate ground truth) ---
# Khi đổi sang du lịch: sửa 2 dòng này
DOMAIN_DESCRIPTION = "big tech companies: Google, NVIDIA, Tesla, and others"
DOMAIN_LANGUAGE = "English"  # hoặc "Vietnamese" khi dùng data du lịch
