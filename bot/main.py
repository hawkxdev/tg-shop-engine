"""Точка входа бота: django.setup(), Dispatcher, RedisStorage."""

import asyncio
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
import structlog

from bot.setup import create_bot, create_dispatcher

logger = structlog.get_logger(__name__)


async def main() -> None:
    """Точка входа: polling или webhook режим."""
    bot = create_bot()
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
