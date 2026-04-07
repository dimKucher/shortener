"""
test_url_service.py — unit-тесты сервисного слоя и утилит.

Тестируем бизнес-логику напрямую, без HTTP:
- generate_short_id()  — генератор коротких идентификаторов
- URLService            — CRUD, идемпотентность, счётчик, retry при коллизии
"""

import string
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from backend.app.services.url_service import URLService
from backend.app.logging import logger
from backend.app.utils.shortener import generate_short_id

# ─── Константы ────────────────────────────────────────────────────────────────

VALID_URL = "https://example.com/some/long/path?query=value"
ANOTHER_URL = "https://another.com/page"
ALPHABET = set(string.ascii_letters + string.digits)


# ═══════════════════════════════════════════════════════════════════════════════
# generate_short_id()
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateShortId:
    """Тесты утилиты генерации коротких идентификаторов."""

    def test_default_length_is_six(self):
        """ID по умолчанию должен быть ровно 6 символов."""
        result = generate_short_id()
        assert len(result) == 6

    def test_custom_length(self):
        """ID должен иметь длину, переданную в аргументе."""
        for length in [4, 8, 12]:
            result = generate_short_id(length)
            assert len(result) == length, f"Ожидали длину {length}, получили {len(result)}"

    def test_only_alphanumeric_characters(self):
        """ID должен содержать только [a-zA-Z0-9], без спецсимволов."""
        for _ in range(100):
            result = generate_short_id()
            assert all(c in ALPHABET for c in result), (
                f"Найден недопустимый символ в '{result}'"
            )

    def test_uniqueness_across_many_generations(self):
        """1000 генераций — не должно быть дубликатов."""
        ids = [generate_short_id() for _ in range(1000)]
        unique_ids = set(ids)
        assert len(unique_ids) == 1000, (
            f"Найдено {1000 - len(unique_ids)} дубликатов из 1000 генераций"
        )

    def test_minimum_length_raises_value_error(self):
        """Длина < 4 должна выбрасывать ValueError."""
        with pytest.raises(ValueError, match="Длина short_id должна быть >= 4"):
            generate_short_id(length=3)

    def test_returns_string(self):
        """Результат должен быть строкой."""
        assert isinstance(generate_short_id(), str)


# ═══════════════════════════════════════════════════════════════════════════════
# URLService.create_short_url()
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateShortUrl:
    """Тесты создания коротких ссылок."""

    @pytest.mark.asyncio
    async def test_returns_url_object_with_correct_fields(self, db_session):
        """Созданная запись должна содержать корректные поля."""
        service = URLService(db_session, logger)
        url_obj = await service.create_short_url(VALID_URL)
        await db_session.commit()

        assert url_obj.original_url == VALID_URL
        assert url_obj.short_id is not None
        assert len(url_obj.short_id) == 6
        assert url_obj.id is not None

    @pytest.mark.asyncio
    async def test_new_url_has_zero_click_count(self, db_session):
        """Новая ссылка должна иметь счётчик переходов равный 0."""
        service = URLService(db_session, logger)
        url_obj = await service.create_short_url(VALID_URL)
        await db_session.commit()

        assert url_obj.click_count == 0

    @pytest.mark.asyncio
    async def test_created_at_is_set(self, db_session):
        """Поле created_at должно быть заполнено автоматически."""
        service = URLService(db_session, logger)
        url_obj = await service.create_short_url(VALID_URL)
        await db_session.commit()

        assert url_obj.created_at is not None

    @pytest.mark.asyncio
    async def test_idempotency_same_url_returns_same_short_id(self, db_session):
        """Повторный вызов с тем же URL должен вернуть тот же short_id."""
        service = URLService(db_session, logger)

        first = await service.create_short_url(VALID_URL)
        await db_session.commit()

        second = await service.create_short_url(VALID_URL)
        await db_session.commit()

        assert first.short_id == second.short_id
        assert first.id == second.id

    @pytest.mark.asyncio
    async def test_different_urls_get_different_short_ids(self, db_session):
        """Разные URL должны получать разные short_id."""
        service = URLService(db_session, logger)

        first = await service.create_short_url(VALID_URL)
        await db_session.commit()

        second = await service.create_short_url(ANOTHER_URL)
        await db_session.commit()

        assert first.short_id != second.short_id

    @pytest.mark.asyncio
    async def test_short_id_contains_only_valid_chars(self, db_session):
        """short_id в БД должен содержать только [a-zA-Z0-9]."""
        service = URLService(db_session, logger)
        url_obj = await service.create_short_url(VALID_URL)
        await db_session.commit()

        assert all(c in ALPHABET for c in url_obj.short_id)

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_all_retries_exhausted(self, db_session):
        """RuntimeError при исчерпании всех попыток генерации уникального ID.

        Имитируем ситуацию, когда generate_short_id
        всегда возвращает одно значение,
        а _short_id_exists всегда возвращает True (ID занят).
        """
        service = URLService(db_session, logger)

        with patch(
                "backend.app.services.url_service.generate_short_id",
                return_value="AAAAAA"
        ):
            with patch.object(
                    service, "_short_id_exists",
                    new=AsyncMock(return_value=True)):
                with pytest.raises(
                        RuntimeError,
                        match="Не удалось сгенерировать уникальный short_id"
                ):
                    await service.create_short_url(ANOTHER_URL)


# ═══════════════════════════════════════════════════════════════════════════════
# URLService.get_by_short_id()
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetByShortId:
    """Тесты поиска по short_id."""

    @pytest.mark.asyncio
    async def test_returns_existing_record(self, db_session):
        """Должен вернуть запись для существующего short_id."""
        service = URLService(db_session, logger)
        created = await service.create_short_url(VALID_URL)
        await db_session.commit()

        found = await service.get_by_short_id(created.short_id)

        assert found is not None
        assert found.short_id == created.short_id
        assert found.original_url == VALID_URL

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_short_id(self, db_session):
        """Должен вернуть None для несуществующего short_id."""
        service = URLService(db_session, logger)

        result = await service.get_by_short_id("XXXXXX")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_string(self, db_session):
        """Должен вернуть None для пустой строки."""
        service = URLService(db_session, logger)

        result = await service.get_by_short_id("")

        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# URLService.increment_click_count()
# ═══════════════════════════════════════════════════════════════════════════════

class TestIncrementClickCount:
    """Тесты счётчика переходов."""

    @pytest.mark.asyncio
    async def test_increments_by_one(self, db_session):
        """После одного инкремента click_count должен стать 1."""
        service = URLService(db_session, logger)
        url_obj = await service.create_short_url(VALID_URL)
        await db_session.commit()

        await service.increment_click_count(url_obj.short_id)
        await db_session.commit()

        updated = await service.get_by_short_id(url_obj.short_id)
        assert updated.click_count == 1

    @pytest.mark.asyncio
    async def test_multiple_increments_accumulate(self, db_session):
        """После N инкрементов click_count должен равняться N."""
        service = URLService(db_session, logger)
        url_obj = await service.create_short_url(VALID_URL)
        await db_session.commit()

        n = 5
        for _ in range(n):
            await service.increment_click_count(url_obj.short_id)
            await db_session.commit()

        updated = await service.get_by_short_id(url_obj.short_id)
        assert updated.click_count == n

    @pytest.mark.asyncio
    async def test_increment_does_not_affect_other_urls(self, db_session):
        """Инкремент одной ссылки не должен затрагивать другую."""
        service = URLService(db_session, logger)

        url_a = await service.create_short_url(VALID_URL)
        url_b = await service.create_short_url(ANOTHER_URL)
        await db_session.commit()

        await service.increment_click_count(url_a.short_id)
        await db_session.commit()

        refreshed_b = await service.get_by_short_id(url_b.short_id)
        assert refreshed_b.click_count == 0

    @pytest.mark.asyncio
    async def test_increment_nonexistent_short_id_does_not_raise(self, db_session):
        """Инкремент несуществующего ID не должен бросать исключение (UPDATE 0 строк)."""
        service = URLService(db_session,logger)

        # Не должно выбросить исключение
        await service.increment_click_count("XXXXXX")
        await db_session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# URLService.get_stats()
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetStats:
    """Тесты получения статистики."""

    @pytest.mark.asyncio
    async def test_returns_correct_stats(self, db_session):
        """get_stats должен возвращать актуальный click_count."""
        service = URLService(db_session, logger)
        url_obj = await service.create_short_url(VALID_URL)
        await db_session.commit()

        await service.increment_click_count(url_obj.short_id)
        await service.increment_click_count(url_obj.short_id)
        await db_session.commit()

        stats = await service.get_stats(url_obj.short_id)

        assert stats is not None
        assert stats.click_count == 2
        assert stats.original_url == VALID_URL

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_short_id(self, db_session):
        """get_stats должен возвращать None для несуществующего short_id."""
        service = URLService(db_session, logger)

        result = await service.get_stats("XXXXXX")

        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# URLService.build_short_url()
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildShortUrl:
    """Тесты формирования полной короткой ссылки."""

    def test_contains_short_id(self, db_session):
        """build_short_url должен содержать переданный short_id."""
        service = URLService(db_session, logger)
        result = service.build_short_url("abc123")

        assert "abc123" in result

    def test_starts_with_base_url(self, db_session):
        """build_short_url должен начинаться с BASE_URL."""
        service = URLService(db_session, logger)
        result = service.build_short_url("abc123")

        assert result.startswith("http")

    def test_no_double_slash(self, db_session):
        """
        build_short_url не должен содержать
        двойной слеш между base и short_id.
        """
        service = URLService(db_session, logger)
        result = service.build_short_url("abc123")

        # Пропускаем схему (http://) и проверяем остаток
        without_scheme = result.split("://", 1)[1]
        assert "//" not in without_scheme
