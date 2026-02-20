"""Обработчики оплаты: СБП через YooKassa, Telegram Stars."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from asgiref.sync import sync_to_async

from payments.services import PaymentService
from shop.models import Order

router = Router(name='payment')


@router.callback_query(F.data.startswith('pay:sbp:'))
async def on_pay_sbp(callback: CallbackQuery, state: FSMContext) -> None:
    """Создать платёж YooKassa СБП и отправить ссылку покупателю."""
    order_id = int(callback.data.split(':')[2])

    try:
        order = await Order.objects.aget(
            id=order_id, user_tg_id=callback.from_user.id
        )
    except Order.DoesNotExist:
        await callback.answer('Заказ не найден.', show_alert=True)
        return

    try:
        result = await sync_to_async(PaymentService.create_sbp_invoice)(order)
    except Exception:
        await callback.answer(
            'Ошибка создания платежа. Попробуйте позже.', show_alert=True
        )
        return

    confirmation_url = result['confirmation_url']
    await callback.message.answer(
        f'Для оплаты заказа №{order.id} перейдите по ссылке:\n{confirmation_url}\n\n'
        'После оплаты статус заказа обновится автоматически.'
    )
    await callback.answer()
