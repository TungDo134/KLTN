"""
MAIN APPLICATION - END POINT
"""

# --- Import ---
import os
from contextlib import asynccontextmanager

import gradio as gr  # Tạm thời tắt Gradio — dùng React Frontend

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pipeline.inference import RAGInference

# --- App Initialization ---
from dotenv import load_dotenv

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

# Cors
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],  # Đọc từ biến môi trường
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str


# --- API Endpoints ---
# @app.get("/")
# async def root():
#     return {"status": "Vietnam Travel RAG API is running 🚀"}


def get_inference_service(request: Request) -> RAGInference:  # ← thêm request
    inference = getattr(request.app.state, "inference", None)
    if inference is None:
        raise HTTPException(status_code=503, detail="Inference Pipeline chưa sẵn sàng!")
    return inference


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, engine: RAGInference = Depends(get_inference_service)
):
    response_text = await engine.predict_async(request.prompt)
    return ChatResponse(response=response_text)


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
