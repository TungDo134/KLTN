from sqlalchemy.orm import Session

from src.models.conversation import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)

    # Lay conversation theo user_id
    def get_conversation_by_user_id(
        self, conversation_id: str, user_id: str
    ) -> Conversation | None:
        return self.conversation_repo.get_conversation_by_user_id(
            conversation_id,
            user_id,
        )

    # Lay LIST conversation theo user_id
    def get_conversations_by_user_id(self, user_id: str):
        return self.conversation_repo.get_conversations_by_user_id(user_id)

    # Lay hoac tao moi conversation
    def get_or_create_conversation(
        self, conversation_id: str | None, user_id: str
    ) -> Conversation:
        """
        - Luu y: neu conversation_id khong hop le hoac da bi soft delete,
        - Ham nay se tao conversation moi thay vi tra loi 404.
        - Se cap nhat lai sau
        """
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

        # Tao title mac dinh
        if not conversation.title:
            conversation.title = user_message[:100]
            self.db.flush()

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

    #
    def get_messages_by_conversation_id(self, conversation_id: str):
        return self.message_repo.get_messages_by_conversation_id(conversation_id)

    # Xoa mem conversation
    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        conversation = self.conversation_repo.get_conversation_by_user_id(
            conversation_id, user_id
        )

        if not conversation:
            return False

        self.conversation_repo.soft_delete_conversation(conversation)
        self.db.commit()
        return True
