"""
MAIN APPLICATION - END POINT
"""

# --- Import ---
import os
from contextlib import asynccontextmanager

import gradio as gr

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


# --- Gradio ChatInterface (Tạm thời tắt — dùng React Frontend) ---


async def gradio_predict(message: str, history: list) -> str:
    """Hàm này được Gradio gọi mỗi khi user gửi tin nhắn."""
    inference: RAGInference = app.state.inference
    if inference is None:
        return "Hệ thống chưa sẵn sàng, vui lòng thử lại sau."
    return await inference.predict_async(message)


gradio_ui = gr.ChatInterface(
    fn=gradio_predict,
    title="🇻🇳 Trợ lý Du lịch Việt Nam",
    description="Hỏi bất kỳ điều gì về du lịch Việt Nam!",
    examples=[
        "Địa điểm du lịch nổi tiếng ở Hội An?",
        "Món ăn đặc sản Hà Nội là gì?",
        "Thời điểm nào đẹp nhất để đến Đà Lạt?",
    ],
)

# Mount Gradio vào FastAPI tại route main /
app = gr.mount_gradio_app(app, gradio_ui, path="/")
