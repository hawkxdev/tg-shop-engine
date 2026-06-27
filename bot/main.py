"""Точка входа бота."""

import asyncio
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from aiogram.types import BotCommand
from django.conf import settings
import structlog

from bot.setup import create_bot, create_dispatcher

_COMMANDS = [
    BotCommand(command='start', description='Начать работу'),
    BotCommand(command='catalog', description='Каталог товаров'),
    BotCommand(command='cart', description='Корзина'),
    BotCommand(command='status', description='Статус заказа'),
    BotCommand(command='help', description='Список команд'),
]

logger = structlog.get_logger(__name__)


async def main() -> None:
    """Запуск бота."""
    bot = create_bot()
    dp = create_dispatcher()

    await bot.set_my_commands(_COMMANDS)

    if settings.WEBHOOK_URL:
        webhook_url = f'{settings.WEBHOOK_URL}/webhook/telegram'
        await bot.set_webhook(webhook_url)
        logger.info(
            'бот_запущен_вебхук',
            webhook_url=webhook_url,
        )
        # Django view принимает updates, bot процесс ожидает
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
