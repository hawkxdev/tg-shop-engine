"""Фабрики Bot и Dispatcher."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from django.conf import settings

from bot.handlers.cart import router as cart_router
from bot.handlers.catalog import router as catalog_router
from bot.handlers.checkout import router as checkout_router
from bot.handlers.order_status import router as order_status_router
from bot.handlers.payment import router as payment_router
from bot.handlers.start import router as start_router
from bot.middlewares.throttling import ThrottlingMiddleware


def create_bot() -> Bot:
    """Создание экземпляра Bot."""
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Создание Dispatcher с роутерами."""
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.include_router(start_router)
    dp.include_router(catalog_router)
    dp.include_router(cart_router)
    dp.include_router(checkout_router)
    dp.include_router(payment_router)
    dp.include_router(order_status_router)
    return dp
