import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.api.deps_chat import get_inference_service
from src.pipeline.inference import RAGInference
from src.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, engine: RAGInference = Depends(get_inference_service)
):
    response_text = await engine.predict_async(
        request.prompt, request.conversationSessionId
    )
    return ChatResponse(response=response_text)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest, engine: RAGInference = Depends(get_inference_service)
):
    async def event_generator():
        async for token in engine.predict_stream(
            request.prompt, request.conversationSessionId
        ):
            yield f"data: {json.dumps(token, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
