from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator
from backend.app.logging import logger


# ─── Request schemas ──────────────────────────────────────────────────────────

class ShortenRequest(BaseModel):
    """Тело запроса POST /shorten."""

    url: AnyHttpUrl = Field(
        ...,
        description="Оригинальный URL для сокращения",
        examples=["https://example.com/very/long/path?query=value"],
    )

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        """Разрешаем только http и https схемы."""
        url_str = str(v)
        if not url_str.startswith(("http://", "https://")):
            logger.exception("URL должен начинаться с http:// или https://")
            raise ValueError("URL должен начинаться с http:// или https://")
        return v


# ─── Response schemas ─────────────────────────────────────────────────────────

class ShortenResponse(BaseModel):
    """Ответ на POST /shorten."""

    model_config = ConfigDict(from_attributes=True)

    short_id: str = Field(..., description="Короткий идентификатор")
    short_url: str = Field(..., description="Полная короткая ссылка")
    original_url: str = Field(..., description="Оригинальный URL")
    created_at: datetime = Field(..., description="Дата создания")


class StatsResponse(BaseModel):
    """Ответ на GET /stats/{short_id}."""

    model_config = ConfigDict(from_attributes=True)

    short_id: str = Field(..., description="Короткий идентификатор")
    original_url: str = Field(..., description="Оригинальный URL")
    click_count: int = Field(..., description="Количество переходов")
    created_at: datetime = Field(..., description="Дата создания")


class ErrorResponse(BaseModel):
    """Стандартный ответ при ошибке."""

    detail: str = Field(..., description="Описание ошибки")
