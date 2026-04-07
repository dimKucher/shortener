# URL Shortener Microservice

# URL Shortener Backend

Асинхронный сервис сокращения URL на FastAPI.

**Реализовано:**
- POST /shorten — создание короткой ссылки
- GET /{short_id} — редирект с подсчётом переходов  
- GET /stats/{short_id} — статистика

**Стек:** FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Docker Compose

**Frontend:** React Native (планируется)

---

## Быстрый старт

### Локально (SQLite, без Docker)

```bash
# 1. Клонируй репозиторий
git clone https://github.com/dimKucher/shortener
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

| Переменная                | По умолчанию / Значение                       | Описание                                                              |
| ------------------------- |-----------------------------------------------| --------------------------------------------------------------------- |
| `CORS_ALLOW_ORIGINS`      | `http://localhost:3000,http://localhost:8000` | Список разрешённых источников (origins) для CORS                      |
| `CORS_ALLOW_ORIGIN_REGEX` | `http://localhost:.*,https://localhost:.*`    | Регулярное выражение для разрешённых источников CORS                  |
| `CORS_ALLOW_METHODS`      | `GET,POST,PUT,DELETE,OPTIONS,HEAD,PATCH`      | Разрешённые HTTP-методы для CORS                                      |
| `CORS_ALLOW_HEADERS`      | `*`                                           | Разрешённые HTTP-заголовки для CORS                                   |
| `CORS_ALLOW_CREDENTIALS`  | `true`                                        | Разрешить использование cookies и авторизации при CORS                |
| `CORS_MAX_AGE`            | `600`                                         | Время (в секундах), на которое браузер кэширует CORS preflight запрос |
| `API_TOKEN`               | `use-your-secret-token`                       | Секретный токен для аутентификации API                                |
| `TOKEN_HEADER_NAME`       | `X-API-Token`                                 | Имя заголовка, в котором ожидается токен                              |
| `DATABASE_URL`            | `sqlite+aiosqlite:///./url_shortener.db`      | Полная строка подключения к БД (используется по умолчанию)            |
| `DB_PREFIX`               | `'postgresql+asyncpg'`                        | Префикс для формирования строки подключения к PostgreSQL              |
| `DB_NAME`                 | `db_name`                                     | Имя базы данных                                                       |
| `DB_USER`                 | `db_user`                                     | Пользователь базы данных                                              |
| `DB_PASSWORD`             | `db_password`                                 | Пароль пользователя базы данных                                       |
| `DB_HOST`                 | `db_host`                                     | Хост базы данных                                                      |
| `DB_PORT`                 | `5432`                                        | Порт базы данных                                                      |
| `BASE_URL`                | `http://localhost:8000`                       | Базовый URL сервиса для генерации коротких ссылок                     |
| `SHORT_ID_LENGTH`         | `6`                                           | Длина короткого идентификатора (минимум 4)                            |



---

## Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# Только unit-тесты сервисного слоя
pytest tests/test_url_service.py -v

# Только интеграционные тесты API
pytest tests/test_api.py -v
```

---

## Архитектура

```
backend/
├ app/
│ ├── config.py         # Настройки через pydantic-settings
│ ├── database.py       # Async engine, сессии, Base
│ ├── models/           # SQLAlchemy ORM модели
│ ├── schemas/          # Pydantic схемы запросов и ответов
│ ├── routers/          # FastAPI роутеры (HTTP слой)
│ ├── services/         # Бизнес-логика (сервисный слой)
│ └── utils/            # Утилиты (генератор short_id)
└──  main.py            # Точка входа FastAPI, lifespan, middleware
```
