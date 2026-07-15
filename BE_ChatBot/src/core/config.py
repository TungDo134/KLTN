"""
Application settings loaded from environment variables.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str | None = None
    sql_echo: bool = False
    firebase_credentials_path: str | None = None
    firebase_credentials_json: str | None = None

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
