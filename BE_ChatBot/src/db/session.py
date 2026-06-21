"""
PostgreSQL SQLAlchemy engine and session dependency.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings


if not settings.database_url:
    raise RuntimeError("DATABASE_URL is not configured in the environment")

# Connection pool - Request tới thì mượn => xong thì trả
# Không cần đóng/mở connection thủ công => tiết kiệm tài nguyên
engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,  # Hiện log SQL
    pool_pre_ping=True,
)

# Factory Config SessionLocal()
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Mỗi request lấy một session DB,
    xử lý query/insert/update => xong thì đóng session
    """
    db = SessionLocal()  # 1. Tạo session (mượn connection từ pool)
    try:
        yield db  # 2. "Cho mượn" session → handler/service dùng
    finally:
        db.close()  # 3. Trả connection về pool (LUÔN LUÔN chạy)
