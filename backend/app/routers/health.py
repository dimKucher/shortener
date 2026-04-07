from fastapi import APIRouter, Depends, status

from backend.app.config import config
from backend.app.logging import logger, get_logger

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Проверка состояния сервиса",
    tags=["Health"],
)
async def health_check(log: logger = Depends(get_logger)) -> dict:
    """GET /health — healthcheck для Docker и мониторинга."""

    log.success(f"✅ Сервис {config.APP_TITLE} работает корректно")

    return {"status": "ok"}
