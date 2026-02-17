# ── Базовый образ ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Копируем uv из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Компиляция байткода для быстрого старта
ENV UV_COMPILE_BYTECODE=1
# Копирование вместо хардлинков (разные файловые системы)
ENV UV_LINK_MODE=copy

WORKDIR /app

# ── Слой зависимостей (кешируется при неизменном lockfile) ──────
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# ── Слой приложения ────────────────────────────────────────────
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ── Финальный образ (без uv, минимальный размер) ───────────────
FROM python:3.11-slim

# Python: не буферизовать stdout/stderr (логи в реальном времени)
ENV PYTHONUNBUFFERED=1

# Создаём непривилегированного пользователя
RUN groupadd --system --gid 999 app \
    && useradd --system --gid 999 --uid 999 --create-home app

# Копируем приложение из builder
COPY --from=builder --chown=app:app /app /app

# Активируем виртуальное окружение через PATH
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Порт Django (gunicorn)
EXPOSE 8000

# Непривилегированный пользователь
USER app

# CMD задаётся в docker-compose.yml (bot или web)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
