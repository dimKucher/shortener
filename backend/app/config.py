from typing import Optional
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Token
    API_TOKEN: str
    TOKEN_HEADER_NAME: str = Field(default="X-API-Token")

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./url_shortener.db"
    DB_PREFIX: str = 'postgresql+asyncpg'
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    # App
    BASE_URL: str = "http://localhost:8000"
    SHORT_ID_LENGTH: int = 6

    # API
    APP_TITLE: str = "URL Shortener API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Микросервис для сокращения ссылок"
    APP_PORT: int = 8000

    # cors
    CORS_ALLOW_ORIGINS: str = Field(default="*")
    CORS_ALLOW_ORIGIN_REGEX: Optional[str] = Field(default=None)
    CORS_ALLOW_METHODS: str = Field(default="*")
    CORS_ALLOW_HEADERS: str = Field(default="*")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_MAX_AGE: int = Field(default=600)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    def get_db_uri(self) -> str:
        return f"{self.DB_PREFIX}://{self.DB_NAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


config = Settings()

CORS_ORIGINS = ["*"] if config.CORS_ALLOW_ORIGINS == "*" else [x.strip() for x in config.CORS_ALLOW_ORIGINS.split(",")]
CORS_METHODS = ["*"] if config.CORS_ALLOW_METHODS == "*" else [x.strip() for x in config.CORS_ALLOW_METHODS.split(",")]
CORS_HEADERS = ["*"] if config.CORS_ALLOW_HEADERS == "*" else [x.strip() for x in config.CORS_ALLOW_HEADERS.split(",")]
