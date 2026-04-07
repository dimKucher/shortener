"""
conftest.py — общие фикстуры для всех тестов.

Архитектурные решения:
- Используем отдельную in-memory SQLite БД (:memory:) — изолированная, быстрая,
  не засоряет файловую систему, каждый тест получает чистое состояние.
- StaticPool гарантирует, что все соединения используют одну и ту же in-memory БД
  (без него каждое соединение создаёт новую пустую БД).
- LifespanManager запускает lifespan FastAPI-приложения (init_db и т.д.).
- Фикстуры с scope="function" — каждый тест получает свежую БД и сессию.
"""

import pytest
import os
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["API_TOKEN"] = "test"
os.environ["DB_NAME"] = "test"
os.environ["DB_USER"] = "test"
os.environ["DB_PASSWORD"] = "test"


from backend.app.database import Base, get_db
from backend.app.app import app
from backend.app.models.url import URL  # noqa: F401 — регистрирует таблицу в Base.metadata

# ─── Тестовая БД ──────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Создаёт async engine на in-memory SQLite для одного теста."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncSession:
    """
    Предоставляет AsyncSession с чистой БД
    для прямого тестирования сервисов.
    """
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine) -> AsyncClient:
    """
    HTTP-клиент с подменённой БД и
    запущенным lifespan приложения.

    Переопределяем dependency get_db так,
    чтобы все запросы к API использовали тестовую in-memory БД.
    """
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_client(client):
    client.headers.update({"X-API-Token": "test"})
    yield client
