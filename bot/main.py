"""Точка входа бота: django.setup(), Dispatcher, RedisStorage."""

import asyncio
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from django.conf import settings
import structlog

from bot.handlers.start import router as start_router
from bot.middlewares.throttling import ThrottlingMiddleware

logger = structlog.get_logger(__name__)


def create_dispatcher() -> Dispatcher:
    """Создаёт Dispatcher с RedisStorage и подключёнными роутерами."""
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    dp.message.middleware(ThrottlingMiddleware())
    dp.include_router(start_router)
    # Роутеры подключаются по мере реализации обработчиков:
    # dp.include_router(...)  # T040: каталог
    # dp.include_router(...)  # T042: корзина
    # dp.include_router(...)  # T045: оформление заказа
    # dp.include_router(...)  # T046: оплата
    # dp.include_router(...)  # T074: статус заказа
    return dp


async def main() -> None:
    """Точка входа: polling или webhook режим."""
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()

    if settings.WEBHOOK_URL:
        webhook_url = f'{settings.WEBHOOK_URL}/webhook/telegram'
        await bot.set_webhook(webhook_url)
        logger.info(
            'бот_запущен_вебхук',
            webhook_url=webhook_url,
        )
        # Обновления принимает Django-представление (T047).
        # Bot-процесс ожидает завершения.
        try:
            await asyncio.Event().wait()
        finally:
            await bot.delete_webhook()
            await bot.session.close()
    else:
        logger.info('бот_запущен_polling')
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
