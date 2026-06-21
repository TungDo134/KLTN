"""
PostgreSQL SQLAlchemy engine and session dependency.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings


if not settings.database_url:
    raise RuntimeError("DATABASE_URL is not configured in the environment")


engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Mỗi request lấy một session DB, xử lý query/insert/update, xong thì đóng session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
