"""Middleware ограничения частоты сообщений."""

from collections.abc import Awaitable, Callable
import time
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Ограничение: 1 сообщение per rate секунд per user.

    Превышающие лимит сообщения отбрасываются без уведомления.
    """

    def __init__(self, rate: float = 0.5) -> None:
        self.rate = rate
        self._last_time: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Проверяет интервал между сообщениями пользователя."""
        user = data.get('event_from_user')
        if user is not None:
            now = time.monotonic()
            last = self._last_time.get(user.id, 0.0)
            if now - last < self.rate:
                return None
            self._last_time[user.id] = now
        return await handler(event, data)
