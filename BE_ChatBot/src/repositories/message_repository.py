from sqlalchemy.orm import Session

from src.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    # Tao moi message dua theo conversation_id
    def create_message(self, conversation_id: str, role: str, content: str) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.db.add(message)
        self.db.flush()
        self.db.refresh(message)
        return message

    #
    def get_messages_by_conversation_id(self, conversation_id: str) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )
