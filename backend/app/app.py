from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import config, CORS_ORIGINS, CORS_METHODS, CORS_HEADERS
from backend.app.database import init_db, close_db
from backend.app.routers.urls import router as url_router
from backend.app.routers.health import router as health_router
from backend.app.routers.root import router as root_router
from backend.app.logging import logger, LoggerConfig


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle менеджер приложения.

    init_db: инициализируем БД (создаём таблицы если не существуют).
    close_db: закрывает соединения с внешними сервисами.
    """
    LoggerConfig()
    await init_db()
    logger.success('🚀 Приложение запущенно успешно')

    yield

    await close_db()
    logger.warning("🛑 Соединение с БД закрыто")


app = FastAPI(
    title=config.APP_TITLE,
    version=config.APP_VERSION,
    description=config.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=config.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
    max_age=config.CORS_MAX_AGE,
)


# ─── Exception handlers ───────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(
        request: Request, exc: Exception
) -> JSONResponse:
    """Ловим все необработанные исключения и возвращаем 500."""
    logger.exception("❌ Внутренняя ошибка сервера")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера"},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

# ─── Root & Health ────────────────────────────────────────────────────────────
app.include_router(root_router, tags=["Root endpoints"])
app.include_router(health_router, tags=["Health check"])

# ─── URL Shortener routes ─────────────────────────────────────────────────────

app.include_router(url_router, tags=["URL Shortener"])
