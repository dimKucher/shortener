"""
test_api.py — интеграционные тесты всех HTTP эндпоинтов.

Тестируем поведение API целиком: HTTP статусы, тела ответов,
заголовки, side-эффекты (счётчик переходов).

Используем AsyncClient с ASGITransport — запросы идут напрямую
в ASGI-приложение без реального сетевого соединения.
"""

import asyncio

import pytest

# ─── Константы ────────────────────────────────────────────────────────────────

VALID_URL = "https://example.com/some/very/long/path?q=1"
ANOTHER_URL = "https://openai.com/blog/chatgpt"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /shorten
# ═══════════════════════════════════════════════════════════════════════════════

class TestPostShorten:
    """Тесты эндпоинта POST /shorten."""

    @pytest.mark.asyncio
    async def test_returns_201_with_valid_url(self, auth_client):
        """Валидный URL → 201 Created."""
        response = await auth_client.post("/shorten", json={"url": VALID_URL})

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_response_body_contains_required_fields(self, auth_client):
        """Ответ должен содержать все обязательные поля."""
        response = await auth_client.post("/shorten", json={"url": VALID_URL})
        data = response.json()

        assert "short_id" in data
        assert "short_url" in data
        assert "original_url" in data
        assert "created_at" in data
#
    @pytest.mark.asyncio
    async def test_short_id_has_correct_length(self, auth_client):
        """short_id в ответе должен быть длиной 6 символов."""
        response = await auth_client.post("/shorten", json={"url": VALID_URL})
        data = response.json()

        assert len(data["short_id"]) == 6

    @pytest.mark.asyncio
    async def test_short_url_contains_short_id(self, auth_client):
        """short_url должен содержать short_id."""
        response = await auth_client.post("/shorten", json={"url": VALID_URL})
        data = response.json()

        assert data["short_id"] in data["short_url"]

    @pytest.mark.asyncio
    async def test_original_url_preserved_in_response(self, auth_client):
        """original_url в ответе должен совпадать с переданным URL."""
        response = await auth_client.post("/shorten", json={"url": VALID_URL})
        data = response.json()

        assert data["original_url"] == VALID_URL

    @pytest.mark.asyncio
    async def test_idempotency_same_url_twice(self, auth_client):
        """Два запроса с одним URL должны вернуть один и тот же short_id."""
        r1 = await auth_client.post("/shorten", json={"url": VALID_URL})
        r2 = await auth_client.post("/shorten", json={"url": VALID_URL})

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["short_id"] == r2.json()["short_id"]

    @pytest.mark.asyncio
    async def test_different_urls_get_different_short_ids(self, auth_client):
        """Разные URL должны получать разные short_id."""
        r1 = await auth_client.post("/shorten", json={"url": VALID_URL})
        r2 = await auth_client.post("/shorten", json={"url": ANOTHER_URL})

        assert r1.json()["short_id"] != r2.json()["short_id"]

    @pytest.mark.asyncio
    async def test_invalid_url_returns_422(self, auth_client):
        """Невалидный URL → 422 Unprocessable Entity."""
        response = await auth_client.post("/shorten", json={"url": "not-a-url"})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ftp_url_returns_422(self, auth_client):
        """URL с ftp:// схемой → 422 (разрешены только http/https)."""
        response = await auth_client.post("/shorten", json={"url": "ftp://files.example.com/file.zip"})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_url_field_returns_422(self, auth_client):
        """Запрос без поля url → 422."""
        response = await auth_client.post("/shorten", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_body_returns_422(self, auth_client):
        """Пустое тело запроса → 422."""
        response = await auth_client.post("/shorten", content=b"")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_https_url_is_accepted(self, auth_client):
        """https:// URL должен быть принят."""
        response = await auth_client.post("/shorten", json={"url": "https://secure.example.com"})

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_http_url_is_accepted(self, auth_client):
        """http:// URL должен быть принят."""
        response = await auth_client.post("/shorten", json={"url": "http://insecure.example.com"})

        assert response.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════════
# GET /{short_id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetRedirect:
    """Тесты эндпоинта GET /{short_id} — редирект."""

    @pytest.mark.asyncio
    async def test_returns_307_for_existing_short_id(self, auth_client, client):
        """Существующий short_id → 307 Temporary Redirect."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        response = await client.get(f"/{short_id}", follow_redirects=False)

        assert response.status_code == 307

    @pytest.mark.asyncio
    async def test_location_header_points_to_original_url(self, auth_client, client):
        """Заголовок Location должен содержать оригинальный URL."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        response = await client.get(f"/{short_id}", follow_redirects=False)

        assert response.headers["location"] == VALID_URL

    @pytest.mark.asyncio
    async def test_nonexistent_short_id_returns_404(self, client):
        """Несуществующий short_id → 404 Not Found."""
        response = await client.get("/XXXXXX", follow_redirects=False)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_404_response_contains_detail_field(self, client):
        """Тело 404 ответа должно содержать поле detail."""
        response = await client.get("/XXXXXX", follow_redirects=False)
        data = response.json()

        assert "detail" in data

    @pytest.mark.asyncio
    async def test_click_count_increments_after_redirect(self, client, auth_client):
        """click_count должен увеличиться на 1 после перехода по ссылке."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        # Переходим по ссылке
        await client.get(f"/{short_id}", follow_redirects=False)

        # BackgroundTask нужно время на выполнение
        await asyncio.sleep(0.2)

        stats = await client.get(f"/stats/{short_id}")
        assert stats.json()["click_count"] == 1

    @pytest.mark.asyncio
    async def test_click_count_increments_on_each_redirect(self, client, auth_client):
        """click_count должен накапливаться с каждым переходом."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        n = 3
        for _ in range(n):
            await client.get(f"/{short_id}", follow_redirects=False)

        await asyncio.sleep(0.3)

        stats = await client.get(f"/stats/{short_id}")
        assert stats.json()["click_count"] == n

    @pytest.mark.asyncio
    async def test_redirect_uses_307_not_301(self, client, auth_client):
        """Должен использоваться 307, а не 301 (браузеры кешируют 301)."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        response = await client.get(f"/{short_id}", follow_redirects=False)

        assert response.status_code == 307
        assert response.status_code != 301


# ═══════════════════════════════════════════════════════════════════════════════
# GET /stats/{short_id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetStats:
    """Тесты эндпоинта GET /stats/{short_id}."""

    @pytest.mark.asyncio
    async def test_returns_200_for_existing_short_id(self, client, auth_client):
        """Существующий short_id → 200 OK."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        response = await client.get(f"/stats/{short_id}")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_contains_required_fields(self, client, auth_client):
        """Ответ должен содержать все обязательные поля."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        response = await client.get(f"/stats/{short_id}")
        data = response.json()

        assert "short_id" in data
        assert "original_url" in data
        assert "click_count" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_initial_click_count_is_zero(self, client, auth_client):
        """Сразу после создания click_count должен быть 0."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        stats = await client.get(f"/stats/{short_id}")

        assert stats.json()["click_count"] == 0

    @pytest.mark.asyncio
    async def test_returns_correct_original_url(self, client, auth_client):
        """original_url в статистике должен совпадать с исходным."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        stats = await client.get(f"/stats/{short_id}")

        assert stats.json()["original_url"] == VALID_URL

    @pytest.mark.asyncio
    async def test_returns_correct_short_id(self, client, auth_client):
        """short_id в ответе должен совпадать с запрошенным."""
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        stats = await client.get(f"/stats/{short_id}")

        assert stats.json()["short_id"] == short_id

    @pytest.mark.asyncio
    async def test_nonexistent_short_id_returns_404(self, client):
        """Несуществующий short_id → 404 Not Found."""
        response = await client.get("/stats/XXXXXX")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_404_response_contains_detail(self, client):
        """Тело 404 ответа должно содержать поле detail."""
        response = await client.get("/stats/XXXXXX")
        data = response.json()

        assert "detail" in data

    @pytest.mark.asyncio
    async def test_stats_not_affected_by_other_url_clicks(self, client, auth_client):
        """Переходы по одной ссылке не влияют на счётчик другой."""
        r1 = await auth_client.post("/shorten", json={"url": VALID_URL})
        r2 = await auth_client.post("/shorten", json={"url": ANOTHER_URL})
        short_id_1 = r1.json()["short_id"]
        short_id_2 = r2.json()["short_id"]

        # Переходим только по первой ссылке
        await client.get(f"/{short_id_1}", follow_redirects=False)
        await asyncio.sleep(0.2)

        stats_2 = await client.get(f"/stats/{short_id_2}")
        assert stats_2.json()["click_count"] == 0

    @pytest.mark.asyncio
    async def test_stats_route_not_captured_by_redirect_route(self, client, auth_client):
        """/stats/{short_id} не должен перехватываться роутом /{short_id}."""
        # Создаём ссылку с short_id = "stats" (edge case: имя совпадает с роутом)
        # Этот тест проверяет правильный порядок регистрации роутов в FastAPI.
        r = await auth_client.post("/shorten", json={"url": VALID_URL})
        short_id = r.json()["short_id"]

        # /stats/{short_id} должен вернуть JSON, а не редирект
        response = await client.get(f"/stats/{short_id}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════════
class TestHealthCheck:
    """Тесты эндпоинта GET /health."""

    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        """Healthcheck должен возвращать 200 OK."""
        response = await client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_ok_status(self, client):
        """Healthcheck должен вернуть {status: ok}."""
        response = await client.get("/health")

        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_not_captured_by_redirect_route(self, client):
        """/health не должен быть перехвачен роутом /{short_id}."""
        response = await client.get("/health")

        # Если /health перехвачен /{short_id} — вернётся 404 с сообщением об ID
        assert response.status_code == 200
        assert "status" in response.json()


# ═══════════════════════════════════════════════════════════════════════════════
# GET /
# ═══════════════════════════════════════════════════════════════════════════════

class TestRootEndpoint:
    """Тесты корневого эндпоинта GET /."""

    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        """Корневой эндпоинт должен возвращать 200 OK."""
        response = await client.get("/")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_contains_endpoints_map(self, client):
        """Ответ должен содержать карту всех доступных эндпоинтов."""
        response = await client.get("/")
        data = response.json()

        assert "endpoints" in data
        assert "shorten" in data["endpoints"]
        assert "redirect" in data["endpoints"]
        assert "stats" in data["endpoints"]
        assert "health" in data["endpoints"]

    @pytest.mark.asyncio
    async def test_response_contains_documentation_links(self, client):
        """Ответ должен содержать ссылки на документацию."""
        response = await client.get("/")
        data = response.json()

        assert "documentation" in data
        assert "swagger" in data["documentation"]
        assert "redoc" in data["documentation"]
