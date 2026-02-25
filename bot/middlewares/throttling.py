"""Middleware ограничения частоты сообщений."""

from collections.abc import Awaitable, Callable
import time
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Rate limiter per user."""

    def __init__(
        self,
        rate: float = 0.5,
        ttl: float = 60.0,
    ) -> None:
        self.rate = rate
        self._ttl = ttl
        self._last_time: dict[int, float] = {}
        self._last_cleanup: float = 0.0

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Проверка интервала сообщений."""
        user = data.get('event_from_user')
        if user is not None:
            now = time.monotonic()
            if now - self._last_cleanup > self._ttl:
                self._cleanup(now)
            last = self._last_time.get(user.id, 0.0)
            if now - last < self.rate:
                return None
            self._last_time[user.id] = now
        return await handler(event, data)

    def _cleanup(self, now: float) -> None:
        """Удаление устаревших записей."""
        cutoff = now - self._ttl
        expired = [k for k, v in self._last_time.items() if v < cutoff]
        for k in expired:
            del self._last_time[k]
        self._last_cleanup = now
