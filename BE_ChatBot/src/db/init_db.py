"""
Initialize tables for an empty deployment PostgreSQL database.
"""

from src.db.base import Base
from src.db.session import engine
from src.models import Conversation, Message, User  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully")


if __name__ == "__main__":
    init_db()
