"""
PostgreSQL SQLAlchemy engine and session dependency.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.core.config import settings


if not settings.database_url:
    raise RuntimeError("DATABASE_URL is not configured in the environment")

# Deployment workload it request: khong giu idle connection khi backend nghi.
engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,  # Hiện log SQL
    poolclass=NullPool,  # Mỗi session sẽ mở connection khi cần và đóng khi kết thúc.
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
    db = SessionLocal()  # 1. Tao session va mo connection khi can
    try:
        yield db  # 2. "Cho mượn" session → handler/service dùng
    finally:
        db.close()  # 3. Dong session va connection (LUON LUON chay)
