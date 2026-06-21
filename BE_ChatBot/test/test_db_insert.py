from uuid import uuid4

from src.db.session import SessionLocal
from src.models.user import User
from src.models.conversation import Conversation
from src.models.message import Message


db = SessionLocal()

try:
    test_id = uuid4().hex
    user = User(
        firebase_uid=f"firebase-test-{test_id}",
        email=f"test-{test_id}@example.com",
        full_name="Firebase Test User",
        avatar_url="https://example.com/avatar.png",
        provider="google",
    )

    db.add(user)
    db.flush()

    conversation = Conversation(
        user_id=user.id,
        title="Test conversation",
    )

    db.add(conversation)
    db.flush()

    message_user = Message(
        conversation_id=conversation.id,
        role="user",
        content="Tôi muốn đi Đà Nẵng 3 ngày 2 đêm",
        metadata_={"intent": "trip_planning", "destination": "Đà Nẵng"},
        token_count=12,
    )

    message_assistant = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="Bạn có thể tham khảo lịch trình Đà Nẵng 3 ngày 2 đêm...",
        metadata_={"model": "test"},
        token_count=20,
    )

    db.add(message_user)
    db.add(message_assistant)
    db.commit()

    print("Insert OK")
    print(f"user_id: {user.id}")
    print(f"firebase_uid: {user.firebase_uid}")
    print(f"conversation_id: {conversation.id}")

except Exception:
    db.rollback()
    raise

finally:
    db.close()
