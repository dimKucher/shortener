# URL Shortener Microservice

Микросервис для сокращения ссылок, аналог Bitly. Написан на **FastAPI** + **SQLAlchemy (async)** + **PostgreSQL/SQLite**.

---

## Быстрый старт

### Локально (SQLite, без Docker)

```bash
# 1. Клонируй репозиторий
git clone <repo-url>
cd url_shortener

# 2. Создай виртуальное окружение
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Настрой окружение
cp .env.example .env           # при необходимости отредактируй .env

# 5. Запусти сервис
uvicorn app.main:app --reload

# Swagger UI: http://localhost:8000/docs
```

### Docker (PostgreSQL)

```bash
# Собери и запусти
docker-compose up --build

# Swagger UI: http://localhost:8000/docs

# Остановить
docker-compose down

# Остановить и удалить данные БД
docker-compose down -v
```

---

## API Reference

### `POST /shorten` — Сократить ссылку

Принимает длинный URL, возвращает короткий идентификатор.  
Если URL уже был сокращён — возвращает существующую запись (идемпотентность).

**Request:**
```json
{
  "url": "https://example.com/very/long/path?query=value"
}
```

**Response `201 Created`:**
```json
{
  "short_id": "aB3xYz",
  "short_url": "http://localhost:8000/aB3xYz",
  "original_url": "https://example.com/very/long/path?query=value",
  "created_at": "2026-04-06T12:00:00Z"
}
```

**Errors:**
- `422` — невалидный URL (не http/https, некорректный формат)

---

### `GET /{short_id}` — Редирект

Перенаправляет на оригинальный URL и увеличивает счётчик переходов.  
Используется `307 Temporary Redirect` — браузеры не кешируют, счётчик всегда обновляется.

**Response `307`:** заголовок `Location: <original_url>`

**Errors:**
- `404` — short_id не найден

---

### `GET /stats/{short_id}` — Статистика

Возвращает количество переходов по ссылке.

**Response `200 OK`:**
```json
{
  "short_id": "aB3xYz",
  "original_url": "https://example.com/very/long/path?query=value",
  "click_count": 42,
  "created_at": "2026-04-06T12:00:00Z"
}
```

**Errors:**
- `404` — short_id не найден

---

### `GET /health` — Healthcheck

```json
{ "status": "ok" }
```

---

## Примеры запросов (curl)

```bash
# Сократить ссылку
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'

# Перейти по короткой ссылке (с отображением редиректа)
curl -L http://localhost:8000/aB3xYz

# Получить статистику
curl http://localhost:8000/stats/aB3xYz

# Healthcheck
curl http://localhost:8000/health
```

---

## Переменные окружения

| Переменная       | По умолчанию                              | Описание                                 |
|------------------|-------------------------------------------|------------------------------------------|
| `DATABASE_URL`   | `sqlite+aiosqlite:///./url_shortener.db`  | Строка подключения к БД                  |
| `BASE_URL`       | `http://localhost:8000`                   | Базовый URL для формирования коротких ссылок |
| `SHORT_ID_LENGTH`| `6`                                       | Длина короткого идентификатора (мин. 4)  |

---

## Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# С отчётом покрытия
pytest tests/ -v --cov=app --cov-report=term-missing

# Только unit-тесты сервисного слоя
pytest tests/test_url_service.py -v

# Только интеграционные тесты API
pytest tests/test_api.py -v
```

---

## Архитектура

```
app/
├── main.py           # Точка входа FastAPI, lifespan, middleware
├── config.py         # Настройки через pydantic-settings
├── database.py       # Async engine, сессии, Base
├── models/           # SQLAlchemy ORM модели
├── schemas/          # Pydantic схемы запросов и ответов
├── routers/          # FastAPI роутеры (HTTP слой)
├── services/         # Бизнес-логика (сервисный слой)
└── utils/            # Утилиты (генератор short_id)
```
