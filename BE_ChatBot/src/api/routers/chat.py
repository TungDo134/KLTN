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


#
def hydrate_conversation_history(
    request: ChatRequest,
    conversation_id: str,
    engine: RAGInference,
    conv_service: ConversationService,
) -> None:
    """
    ### Bridge giua API layer & Inference
        - Quyet dinh xem co load history tu DB khong
        => Call service + RAGInference de lam (`hydrate_history`)
        ```
    FE/Postman gửi conversation_id
            ↓
    chat.py get_or_create_conversation()
            ↓
    hydrate_conversation_history()
            ↓
    query messages từ DB
            ↓
    RAGInference.hydrate_history()
            ↓

        ```
    """

    # Neu request ko co conversation_id => new conversation
    # => Ko co msg cũ
    if not request.conversation_id:
        return

    # Co conversation_id => user dg tiep tuc chat tu conversation cũ
    # => Query db lay msg tuong ung
    messages = conv_service.get_messages_by_conversation_id(conversation_id)

    # Dua msg tu DB vao RAGInference
    engine.hydrate_history(conversation_id, messages)


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
    hydrate_conversation_history(
        request,
        conversation.id,
        engine,
        conv_service,
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

    hydrate_conversation_history(
        request,
        conversation.id,
        engine,
        conv_service,
    )

    async def event_generator():
        """
        - SSE (gui tung event - startWith 'Data')
        - Phan biet moi line = dau xuong dong
        """
        meta = json.dumps({"conversation_id": conversation_id}, ensure_ascii=False)
        yield f"event: meta\ndata: {meta}\n\n"

        full_response = ""
        async for token in engine.predict_stream(
            request.prompt,
            conversation_id,
            retrieval_vector_weight=request.retrieval_vector_weight,
            recommendation_content_weight=request.recommendation_content_weight,
        ):
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
