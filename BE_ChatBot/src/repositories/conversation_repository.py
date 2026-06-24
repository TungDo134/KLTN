from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    # Lay conversation theo user id
    def get_conversation_by_user_id(
        self, conversation_id: str, user_id: str
    ) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .first()
        )

    # Tao moi conversation
    def create_conversation(
        self, user_id: str, title: str | None = None
    ) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.flush()
        self.db.refresh(conversation)
        return conversation

    # Update value `updated_at`
    def touch_updated_at(self, conversation: Conversation) -> None:
        conversation.updated_at = func.now()
        self.db.flush()
