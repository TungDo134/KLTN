from fastapi import APIRouter, Depends

from src.api.deps_chat import get_inference_service
from src.pipeline.inference import RAGInference
from src.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, engine: RAGInference = Depends(get_inference_service)
):
    response_text = await engine.predict_async(request.prompt)
    return ChatResponse(response=response_text)
