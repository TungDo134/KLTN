import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.api.deps_chat import get_inference_service
from src.db.session import get_db
from src.models.user import User
from src.pipeline.inference import RAGInference
from src.schemas.chat import ChatRequest, ChatResponse
from src.services.conversation_service import ConversationService

router = APIRouter(tags=["chat"])


# non-stream response
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    engine: RAGInference = Depends(get_inference_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    conversation = conv_service.get_or_create_conversation(
        request.conversation_id, current_user.id
    )

    response_text = await engine.predict_async(request.prompt, conversation.id)

    conv_service.save_turn(
        conversation.id, current_user.id, request.prompt, response_text
    )
    return ChatResponse(response=response_text)


# stream response
@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    engine: RAGInference = Depends(get_inference_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    conversation = conv_service.get_or_create_conversation(
        request.conversation_id,
        current_user.id,
    )
    conversation_id = conversation.id

    #
    async def event_generator():
        """
        - SSE (gui tung event - startWith 'Data')
        - Phan biet moi line = dau xuong dong \ n \ n
        """
        meta = json.dumps({"conversation_id": conversation_id}, ensure_ascii=False)
        yield f"event: meta\ndata: {meta}\n\n"

        full_response = ""
        async for token in engine.predict_stream(request.prompt, conversation_id):
            full_response += token
            yield f"data: {json.dumps(token, ensure_ascii=False)}\n\n"

        conv_service.save_turn(
            conversation_id,
            current_user.id,
            request.prompt,
            full_response,
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
