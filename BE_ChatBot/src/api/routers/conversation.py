from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.user import User
from src.schemas.chat import ConversationSummary, MessageResponse
from src.services.conversation_service import ConversationService


router = APIRouter(prefix="/conversations", tags=["conversation"])


# Lay danh sach conversations cua current user
@router.get("", response_model=list[ConversationSummary])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    return conv_service.get_conversations_by_user_id(current_user.id)


# Lay messsages tuong ung voi conversation theo conversation_id
@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    conversation = conv_service.get_conversation_by_user_id(
        conversation_id, current_user.id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="conversation not found")

    return conv_service.get_messages_by_conversation_id(conversation_id)


# Xoa mem conversation
@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_service = ConversationService(db)
    deleted = conv_service.delete_conversation(conversation_id, current_user.id)

    if not deleted:
        raise HTTPException(status_code=404, detail="conversation not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
