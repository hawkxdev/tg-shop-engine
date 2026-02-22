"""Обработчик команды /status — статус последнего заказа."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from shop.models import Order

router = Router(name='order_status')

_NO_ORDERS = 'У вас ещё нет заказов.'


async def on_status(message: Message) -> None:
    """Показать статус последнего заказа пользователя."""
    user_tg_id = message.from_user.id

    order = (
        await Order.objects.filter(user_tg_id=user_tg_id)
        .order_by('-created_at')
        .afirst()
    )

    if not order:
        await message.answer(_NO_ORDERS)
        return

    text = (
        f'Заказ: {order.uuid}\n'
        f'Статус: {order.get_status_display()}\n'
        f'Сумма: {order.total} ₽'
    )
    await message.answer(text)


router.message(Command('status'))(on_status)
