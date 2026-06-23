from sqlalchemy.orm import Session

from src.models.conversation import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)

    # Lay hoac tao moi conversation
    def get_or_create_conversation(
        self, conversation_id: str | None, user_id: str
    ) -> Conversation:
        # Co id => kim conver match
        if conversation_id:
            conversation = self.conversation_repo.get_conversation_by_user_id(
                conversation_id, user_id
            )
            # Tra ve conver match
            if conversation:
                return conversation

        # Khong co id => tao moi conver
        conversation = self.conversation_repo.create_conversation(user_id=user_id)
        self.db.commit()
        return conversation

    # Luu message
    def save_turn(
        self, conversation_id: str, user_id: str, user_message: str, bot_response: str
    ) -> None:
        conversation = self.conversation_repo.get_conversation_by_user_id(
            conversation_id, user_id
        )

        if not conversation:
            return

        self.message_repo.create_message(
            conversation_id, role="user", content=user_message
        )
        self.message_repo.create_message(
            conversation_id,
            role="assistant",
            content=bot_response,
        )
        self.conversation_repo.touch_updated_at(conversation)
        self.db.commit()
