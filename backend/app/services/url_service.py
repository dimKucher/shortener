from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import config
from backend.app.models.url import URL
from backend.app.utils.shortener import generate_short_id
from backend.app.logging import logger

_MAX_RETRIES = 5    # Максимум попыток генерации уникального ID перед ошибкой


class URLService:
    """Сервисный слой: вся бизнес-логика работы с сокращёнными ссылками."""

    def __init__(self, db: AsyncSession, log: logger) -> None:
        self._db = db
        self._log = log

    async def create_short_url(self, original_url: str) -> URL:
        """Создаёт новую сокращённую ссылку.

        Если URL уже существует — возвращает существующую запись.
        Генерирует уникальный short_id с защитой от коллизий.

        Args:
            original_url: оригинальный URL для сокращения

        Returns:
            Объект URL из БД

        Raises:
            RuntimeError: если не удалось сгенерировать уникальный ID за _MAX_RETRIES попыток
        """
        existing = await self._get_by_original_url(original_url)
        if existing:
            self._log.warning(
                f"Такая сокращенная ссылка уже существует {existing.short_id}"
            )
            return existing

        short_id = await self._generate_unique_short_id()

        url_obj = URL(short_id=short_id, original_url=original_url, click_count=0)
        self._db.add(url_obj)
        await self._db.flush()
        await self._db.refresh(url_obj)

        self._log.success(
            f"Новая сокращенная ссылка создана успешна {url_obj.short_id}"
        )

        return url_obj

    async def get_by_short_id(self, short_id: str) -> URL | None:
        """Находит запись по short_id.

        Args:
            short_id: короткий идентификатор

        Returns:
            Объект URL или None если не найден
        """
        stmt = select(URL).where(URL.short_id == short_id)
        result = await self._db.execute(stmt)

        url = result.scalar_one_or_none()
        if not url:
            self._log.warning(f"Сокращенная ссылка не существует")
        # self._log.info(f"Ссылка  {url.short_id}")

        return url

    async def increment_click_count(self, short_id: str) -> None:
        """Атомарно увеличивает счётчик переходов на 1.

        Использует UPDATE ... SET click_count = click_count + 1.

        Args:
            short_id: короткий идентификатор
        """
        stmt = (
            update(URL)
            .where(URL.short_id == short_id)
            .values(click_count=URL.click_count + 1)
        )
        self._log.info(
            f"Счётчик переходов  по сокращенной ссылки {short_id} увеличен +1"
        )
        await self._db.execute(stmt)

    async def get_stats(self, short_id: str) -> URL | None:
        """Возвращает статистику по short_id.

        Args:
            short_id: короткий идентификатор

        Returns:
            Объект URL со статистикой или None
        """
        return await self.get_by_short_id(short_id)

    def build_short_url(self, short_id: str) -> str:
        """Собирает полную короткую ссылку из base URL и short_id."""
        return f"{config.BASE_URL.rstrip('/')}/{short_id}"

    async def _get_by_original_url(self, original_url: str) -> URL | None:
        """Ищет существующую запись по оригинальному URL."""
        stmt = select(URL).where(URL.original_url == original_url)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _short_id_exists(self, short_id: str) -> bool:
        """Проверяет, занят ли short_id."""
        stmt = select(URL.id).where(URL.short_id == short_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _generate_unique_short_id(self) -> str:
        """Генерирует short_id, гарантированно уникальный в БД.

        Raises:
            RuntimeError: если за _MAX_RETRIES попыток не нашли свободный ID
        """
        for attempt in range(1, _MAX_RETRIES + 1):
            candidate = generate_short_id(config.SHORT_ID_LENGTH)
            if not await self._short_id_exists(candidate):
                return candidate

        raise RuntimeError(
            f"Не удалось сгенерировать уникальный short_id "
            f"за {_MAX_RETRIES} попыток. "
            f"Рассмотрите увеличение SHORT_ID_LENGTH."
        )
