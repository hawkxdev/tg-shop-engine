"""Обработчики оплаты."""

import contextlib

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from asgiref.sync import sync_to_async

from payments.services import PaymentService
from shop.models import Order

router = Router(name='payment')


@router.callback_query(F.data.startswith('pay:sbp:'))
async def on_pay_sbp(callback: CallbackQuery) -> None:
    """Создание платежа СБП."""
    msg = callback.message
    if not callback.data or not isinstance(msg, Message):
        return
    order_id = int(callback.data.split(':')[2])

    try:
        order = await Order.objects.aget(
            id=order_id,
            user_tg_id=callback.from_user.id,
        )
    except Order.DoesNotExist:
        await callback.answer('Заказ не найден.', show_alert=True)
        return

    try:
        result = await sync_to_async(PaymentService.create_sbp_invoice)(order)
    except Exception:
        await callback.answer(
            'Ошибка создания платежа. Попробуйте позже.',
            show_alert=True,
        )
        return

    confirmation_url = result['confirmation_url']
    await msg.answer(
        f'Для оплаты заказа №{order.id} перейдите по '
        f'ссылке:\n{confirmation_url}\n\n'
        'После оплаты статус заказа обновится '
        'автоматически.'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('pay:stars:'))
async def on_pay_stars(callback: CallbackQuery) -> None:
    """Создание Stars инвойса."""
    msg = callback.message
    if not callback.data or not isinstance(msg, Message):
        return
    order_id = int(callback.data.split(':')[2])

    try:
        order = await Order.objects.aget(
            id=order_id,
            user_tg_id=callback.from_user.id,
        )
    except Order.DoesNotExist:
        await callback.answer('Заказ не найден.', show_alert=True)
        return

    try:
        invoice = await sync_to_async(PaymentService.create_stars_invoice)(
            order
        )
    except Exception:
        await callback.answer(
            'Ошибка создания платежа. Попробуйте позже.',
            show_alert=True,
        )
        return

    prices = [
        LabeledPrice(label=p['label'], amount=p['amount'])
        for p in invoice['prices']
    ]

    await msg.answer_invoice(
        title=invoice['title'],
        description=f'Оплата заказа #{order.id}',
        payload=invoice['payload'],
        currency=invoice['currency'],
        prices=prices,
        provider_token='',
    )
    await callback.answer()


@router.pre_checkout_query()
async def on_pre_checkout_query(
    query: PreCheckoutQuery,
) -> None:
    """Проверка наличия товаров."""
    payload = query.invoice_payload

    try:
        order = await Order.objects.aget(uuid=payload)
    except Order.DoesNotExist:
        await query.answer(ok=False, error_message='Заказ не найден.')
        return

    async for item in order.items.select_related('product').all():
        if item.product.stock < item.quantity:
            await query.answer(
                ok=False,
                error_message=(f'{item.product_name} нет в наличии.'),
            )
            return

    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    """Обработка успешного платежа."""
    if not message.from_user or not message.successful_payment:
        return
    sp = message.successful_payment

    await sync_to_async(PaymentService.handle_stars_payment)(
        user_id=message.from_user.id,
        payload=sp.invoice_payload,
        charge_id=sp.telegram_payment_charge_id,
        amount=sp.total_amount,
    )

    with contextlib.suppress(Exception):
        from bot.services.notification import (
            NotificationService,
        )

        order = await Order.objects.aget(uuid=sp.invoice_payload)
        await NotificationService.notify_buyer(
            bot=message.bot,
            user_tg_id=message.from_user.id,
            order=order,
            event='payment_success',
        )

    await message.answer(
        'Оплата прошла успешно! Спасибо за заказ.\nСтатус заказа обновлён.'
    )
