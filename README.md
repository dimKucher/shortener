<div align="center">

# 🔗 URL Shortener Microservice

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![React Native](https://img.shields.io/badge/React_Native-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactnative.dev/)

**Асинхронный сервис сокращения URL на FastAPI**

[Документация API](#-api-reference) • [Быстрый старт](#-быстрый-старт) • [Docker](#-docker) • [Архитектура](#-архитектура)

</div>

---

## ✨ Реализовано

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/shorten` | `POST` | Создание короткой ссылки |
| `/{short_id}` | `GET` | Редирект с подсчётом переходов |
| `/stats/{short_id}` | `GET` | Статистика переходов |
| `/health` | `GET` | Проверка состояния сервиса |

## 🛠 Технологический стек

<div align="center">

| Категория | Технологии |
|-----------|------------|
| **Framework** | ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi) |
| **Язык** | ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python) |
| **ORM** | ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=flat-square&logo=sqlalchemy) |
| **База данных** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite) |
| **Контейнеризация** | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker) ![Docker Compose](https://img.shields.io/badge/Docker_Compose-2496ED?style=flat-square&logo=docker) |
| **Валидация** | ![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic) |
| **Логирование** | ![Loguru](https://img.shields.io/badge/Loguru-000000?style=flat-square) |

**Frontend (в планах):** ![React Native](https://img.shields.io/badge/React_Native-20232A?style=flat-square&logo=react) ![Expo](https://img.shields.io/badge/Expo-000020?style=flat-square&logo=expo)

</div>

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
