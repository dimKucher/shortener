from fastapi import APIRouter, FastAPI, Request, status

from backend.app.config import config


router = APIRouter()


@router.get("/", include_in_schema=False)
async def root(request: Request) -> dict:
    """
    Возвращает информацию о сервисе и
    список всех доступных эндпоинтов.
    """
    base = config.BASE_URL.rstrip("/")

    return {
        "service": config.APP_TITLE,
        "version": config.APP_VERSION,
        "endpoints": {
            "shorten": {
                "method": "POST",
                "url": f"{base}/shorten",
                "description": "Сократить ссылку"
            },
            "redirect": {
                "method": "GET",
                "url": f"{base}/{{short_id}}",
                "description": "Перейти по короткой ссылке"
            },
            "stats": {
                "method": "GET",
                "url": f"{base}/stats/{{short_id}}",
                "description": "Статистика переходов"
            },
            "health": {
                "method": "GET",
                "url": f"{base}/health",
                "description": "Healthcheck"
            },
        },
        "documentation": {
            "swagger": f"{base}/docs",
            "redoc": f"{base}/redoc",
        },
    }