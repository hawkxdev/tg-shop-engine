"""Обработчики FSM оформления заказа: имя, телефон, адрес, промокод, подтверждение."""

from decimal import Decimal
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from asgiref.sync import sync_to_async
from django.conf import settings

from bot.keyboards.checkout import (
    address_confirm_keyboard,
    cancel_keyboard,
    order_confirm_keyboard,
    payment_method_keyboard,
    promo_keyboard,
)
from bot.states.checkout import CheckoutState
from shop.services.address import AddressService
from shop.services.order import InsufficientStockError, OrderService
from shop.services.promo import PromoService

router = Router(name='checkout')

_PHONE_RE = re.compile(
    r'^(\+7|7|8)[\s\-\(]?(\d{3})[\s\-\)]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})$'
)
_CANCEL_MSG = 'Оформление отменено. Корзина сохранена.'
_DELIVERY_COST = Decimal(str(getattr(settings, 'DELIVERY_COST', 300) or 300))


def _cart_subtotal(cart: dict) -> Decimal:
    """Подсчитать сумму товаров в корзине."""
    return sum(Decimal(item['price']) * item['qty'] for item in cart.values())


def _order_summary_text(data: dict) -> str:
    """Сформировать текст сводки заказа для подтверждения."""
    cart = data.get('cart', {})
    subtotal = _cart_subtotal(cart)
    discount_amount = Decimal(data.get('discount_amount', '0'))
    delivery_cost = Decimal(
        data.get('promo_delivery_cost', str(_DELIVERY_COST))
    )
    total = subtotal + delivery_cost - discount_amount

    lines = ['<b>Ваш заказ:</b>\n']
    for item in cart.values():
        item_total = Decimal(item['price']) * item['qty']
        lines.append(f'• {item["name"]} × {item["qty"]} = {item_total} ₽')
    lines.append(f'\nПолучатель: {data.get("name", "")}')
    lines.append(f'Телефон: {data.get("phone", "")}')
    lines.append(f'Адрес: {data.get("address", "")}')
    lines.append(f'\nСтоимость товаров: {subtotal} ₽')
    lines.append(f'Доставка: {delivery_cost} ₽')
    promo = data.get('promo_code')
    if promo:
        lines.append(f'Промокод: {promo}')
        if discount_amount > 0:
            lines.append(f'Скидка: -{discount_amount} ₽')
    lines.append(f'<b>Итого: {total} ₽</b>')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Шаг 1: Имя
# ---------------------------------------------------------------------------


@router.message(CheckoutState.waiting_name)
async def on_waiting_name(message: Message, state: FSMContext) -> None:
    """Принять имя пользователя."""
    name = (message.text or '').strip()
    if not name:
        await message.answer(
            'Имя не может быть пустым. Введите ваше имя:',
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(name=name)
    await state.set_state(CheckoutState.waiting_phone)
    await message.answer(
        f'Отлично, {name}! Теперь введите номер телефона (например: +79991234567):',
        reply_markup=cancel_keyboard(),
    )


# ---------------------------------------------------------------------------
# Шаг 2: Телефон
# ---------------------------------------------------------------------------


@router.message(CheckoutState.waiting_phone)
async def on_waiting_phone(message: Message, state: FSMContext) -> None:
    """Принять и валидировать российский номер телефона."""
    phone = (message.text or '').strip().replace(' ', '')
    if not _PHONE_RE.match(phone):
        await message.answer(
            'Некорректный номер. Введите телефон в формате +79991234567:',
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(CheckoutState.waiting_address)
    await message.answer(
        'Введите адрес доставки (город, улица, дом):',
        reply_markup=cancel_keyboard(),
    )


# ---------------------------------------------------------------------------
# Шаг 3: Адрес
# ---------------------------------------------------------------------------


@router.message(CheckoutState.waiting_address)
async def on_waiting_address(message: Message, state: FSMContext) -> None:
    """Принять адрес, нормализовать через DaData и отправить на подтверждение."""
    raw_address = (message.text or '').strip()
    if not raw_address:
        await message.answer(
            'Адрес не может быть пустым. Введите адрес доставки:',
            reply_markup=cancel_keyboard(),
        )
        return

    result = await AddressService.normalize_address(raw_address)
    normalized = result['normalized']
    quality_code = result['quality_code']

    await state.update_data(
        address=normalized,
        address_raw=raw_address,
    )
    await state.set_state(CheckoutState.confirm_address)

    quality_note = ''
    if quality_code < 0:
        quality_note = (
            '\n⚠️ Адрес не удалось нормализовать, будет использован как есть.'
        )

    await message.answer(
        f'Адрес доставки:\n<b>{normalized}</b>{quality_note}\n\nВсё верно?',
        reply_markup=address_confirm_keyboard(),
        parse_mode='HTML',
    )


# ---------------------------------------------------------------------------
# Шаг 3а: Подтверждение адреса
# ---------------------------------------------------------------------------


@router.callback_query(
    CheckoutState.confirm_address, F.data == 'address:confirm'
)
async def on_address_confirm(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Принять нормализованный адрес и перейти к промокоду."""
    await state.set_state(CheckoutState.waiting_promo)
    await callback.message.edit_text(
        'Есть промокод? Введите его или пропустите этот шаг.',
        reply_markup=promo_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    CheckoutState.confirm_address, F.data == 'address:retry'
)
async def on_address_retry(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к вводу адреса."""
    await state.set_state(CheckoutState.waiting_address)
    await callback.message.edit_text(
        'Введите адрес доставки (город, улица, дом):',
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 4: Промокод
# ---------------------------------------------------------------------------


@router.message(CheckoutState.waiting_promo)
async def on_waiting_promo(message: Message, state: FSMContext) -> None:
    """Принять и валидировать промокод через PromoService."""
    code = (message.text or '').strip().upper()
    if not code:
        await message.answer(
            'Введите промокод или нажмите «Пропустить».',
            reply_markup=promo_keyboard(),
        )
        return

    data = await state.get_data()
    cart = data.get('cart', {})
    subtotal = _cart_subtotal(cart)

    promo = await sync_to_async(PromoService.validate_code)(
        code=code,
        user_tg_id=message.from_user.id,
        subtotal=subtotal,
    )
    if promo is None:
        await message.answer(
            'Промокод недействителен или не может быть применён.\n'
            'Попробуйте другой или нажмите «Пропустить».',
            reply_markup=promo_keyboard(),
        )
        return

    discount_amount, new_delivery = await sync_to_async(
        PromoService.apply_discount
    )(
        subtotal=subtotal,
        delivery_cost=_DELIVERY_COST,
        promo=promo,
    )
    await state.update_data(
        promo_code=code,
        promo_id=promo.pk,
        discount_amount=str(discount_amount),
        promo_delivery_cost=str(new_delivery),
    )
    await _show_order_summary(message, state, edit=False)


@router.callback_query(CheckoutState.waiting_promo, F.data == 'promo:skip')
async def on_promo_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропустить ввод промокода."""
    await state.update_data(promo_code=None)
    await state.set_state(CheckoutState.confirm_order)
    data = await state.get_data()
    await callback.message.edit_text(
        _order_summary_text(data),
        reply_markup=order_confirm_keyboard(),
        parse_mode='HTML',
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 5: Подтверждение заказа
# ---------------------------------------------------------------------------


@router.callback_query(CheckoutState.confirm_order, F.data == 'order:confirm')
async def on_order_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Создать заказ из FSM-данных и перейти к выбору оплаты."""
    data = await state.get_data()
    cart = data.get('cart', {})

    cart_items = {int(pid): item['qty'] for pid, item in cart.items()}

    # Загружаем промокод из БД, если был применён
    promo = None
    promo_id = data.get('promo_id')
    if promo_id:
        from shop.models import PromoCode
        promo = await sync_to_async(
            PromoCode.objects.get
        )(pk=promo_id)

    delivery_cost = Decimal(
        data.get('promo_delivery_cost', str(_DELIVERY_COST))
    )

    try:
        order = await sync_to_async(OrderService.create_order)(
            user_tg_id=callback.from_user.id,
            user_name=data['name'],
            user_phone=data['phone'],
            user_address=data['address'],
            user_address_raw=data.get('address_raw'),
            cart_items=cart_items,
            promo=promo,
            delivery_cost=delivery_cost,
        )
    except InsufficientStockError as exc:
        await callback.message.answer(
            f'❌ Недостаточно товара на складе: {exc}\n'
            'Скорректируйте корзину и попробуйте снова.'
        )
        await callback.answer()
        return

    await state.update_data(cart={}, order_id=order.id)
    await state.set_state(CheckoutState.waiting_payment)
    await callback.message.edit_text(
        f'✅ Заказ №{order.id} создан!\n\nВыберите способ оплаты:',
        reply_markup=payment_method_keyboard(order.id),
    )
    await callback.answer()


@router.callback_query(CheckoutState.confirm_order, F.data == 'order:cancel')
async def on_order_cancel_confirm(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Отменить заказ на шаге подтверждения (корзина сохраняется)."""
    await _cancel_checkout(callback, state)


# ---------------------------------------------------------------------------
# Отмена на любом шаге
# ---------------------------------------------------------------------------


@router.callback_query(F.data == 'checkout:cancel')
async def on_checkout_cancel(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Отменить оформление заказа и сохранить корзину."""
    await _cancel_checkout(callback, state)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


async def _show_order_summary(
    message: Message, state: FSMContext, *, edit: bool
) -> None:
    """Показать сводку заказа для подтверждения."""
    await state.set_state(CheckoutState.confirm_order)
    data = await state.get_data()
    text = _order_summary_text(data)
    if edit:
        await message.edit_text(
            text, reply_markup=order_confirm_keyboard(), parse_mode='HTML'
        )
    else:
        await message.answer(
            text, reply_markup=order_confirm_keyboard(), parse_mode='HTML'
        )


async def _cancel_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    """Сбросить FSM, сохранив корзину."""
    data = await state.get_data()
    cart = data.get('cart', {})
    await state.clear()
    if cart:
        await state.update_data(cart=cart)
    await callback.message.answer(_CANCEL_MSG)
    await callback.answer()
