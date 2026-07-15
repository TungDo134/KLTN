"""
MAIN APPLICATION - END POINT
"""

# --- Import ---
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .api.routers import auth, chat, conversation
from .pipeline.inference import RAGInference

# --- App Initialization ---

load_dotenv()


# Quản lý vòng đời app
inference_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo RAGInference 1 lần khi app start, giải phóng khi app stop."""
    print("\n ================ KHỞI ĐỘNG ỨNG DỤNG - HẾ LÔ ================")
    app.state.inference = RAGInference()
    print(
        "\n ================ ỨNG DỤNG SẴN SÀNG - HỎI ĐI TUI TRẢ LỜI CHO ================"
    )

    yield
    print("\n ================ TẮT ỨNG DỤNG - BÁI BAI NHA ================ \n")
    app.state.inference = None


app = FastAPI(title="Vietnam Travel RAG API", lifespan=lifespan)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(conversation.router)

# Cors
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],  # Đọc từ biến môi trường
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
