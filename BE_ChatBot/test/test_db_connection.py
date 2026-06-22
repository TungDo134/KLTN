from sqlalchemy import text

from src.db.session import engine
from src.db.session import SessionLocal

from src.models.user import User
from src.models.conversation import Conversation
from src.models.message import Message

# with engine.connect() as conn:
#     result = conn.execute(text("SELECT version();"))
#     print(result.scalar())


db = SessionLocal()

try:
    print("Testing SQLAlchemy model mapping...")

    user_count = db.query(User).count()
    conversation_count = db.query(Conversation).count()
    message_count = db.query(Message).count()

    print(f"users: {user_count}")
    print(f"conversations: {conversation_count}")
    print(f"messages: {message_count}")

    print("Model mapping OK")

finally:
    db.close()
