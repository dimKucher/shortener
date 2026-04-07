from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.schemas.urls import (
    ErrorResponse,
    ShortenRequest,
    ShortenResponse,
    StatsResponse
)
from backend.app.services.url_service import URLService
from backend.app.logging import get_logger, logger
from backend.app.services.auth_service import token_auth

router = APIRouter()


def get_url_service(
        db: AsyncSession = Depends(get_db),
        log=Depends(get_logger)
) -> URLService:
    """Dependency: создаёт экземпляр URLService с текущей сессией БД."""
    return URLService(db, log)


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Сократить ссылку",
    description="Принимает длинный URL и "
                "возвращает короткий идентификатор. "
                "Если URL уже был сокращён ранее — "
                "возвращает существующую запись.",
    responses={
        422: {"model": ErrorResponse, "description": "Невалидный URL"},
    },
    dependencies=[Depends(token_auth.verify_token)]
)
async def shorten_url(
        body: ShortenRequest,
        service: URLService = Depends(get_url_service)
) -> ShortenResponse:
    """POST /shorten — создать короткую ссылку."""
    original_url = str(body.url)
    url_obj = await service.create_short_url(original_url)
    return ShortenResponse(
        short_id=url_obj.short_id,
        short_url=service.build_short_url(url_obj.short_id),
        original_url=url_obj.original_url,
        created_at=url_obj.created_at,
    )


@router.get(
    "/stats/{short_id}",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Статистика переходов",
    description="Возвращает количество переходов по короткой ссылке.",
    responses={
        404: {"model": ErrorResponse, "description": "Ссылка не найдена"},
    },
)
async def get_stats(
        short_id: str,
        service: URLService = Depends(get_url_service),
        log: logger = Depends(get_logger)
) -> StatsResponse:
    """GET /stats/{short_id} — статистика по короткой ссылке."""
    url_obj = await service.get_stats(short_id)

    if url_obj is None:
        log.exception(f"Ссылка с идентификатором '{short_id}' не найдена")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ссылка с идентификатором '{short_id}' не найдена",
        )

    return StatsResponse(
        short_id=url_obj.short_id,
        original_url=url_obj.original_url,
        click_count=url_obj.click_count,
        created_at=url_obj.created_at,
    )


@router.get(
    "/{short_id}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Редирект по короткой ссылке",
    description="Перенаправляет на оригинальный URL "
                "и увеличивает счётчик переходов. "
                "Используется 307, чтобы браузеры не кешировали редирект — "
                "иначе счётчик не будет обновляться.",
    responses={
        307: {"description": "Редирект на оригинальный URL"},
        404: {"model": ErrorResponse, "description": "Ссылка не найдена"},
    },
)
async def redirect_to_original(
        short_id: str,
        background_tasks: BackgroundTasks,
        service: URLService = Depends(get_url_service),
        log: logger = Depends(get_logger)
) -> RedirectResponse:
    """
    GET /{short_id} — редирект на оригинальный URL.

    Счётчик обновляется через BackgroundTasks —
    после отправки редиректа,
    чтобы не задерживать ответ пользователю.
    """
    url_obj = await service.get_by_short_id(short_id)

    if url_obj is None:
        log.exception(f"Ссылка с идентификатором '{short_id}' не найдена")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ссылка с идентификатором '{short_id}' не найдена",
        )
    log.success(f"Полная ссылка {url_obj.original_url}")
    background_tasks.add_task(service.increment_click_count, short_id)

    return RedirectResponse(
        url=url_obj.original_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
