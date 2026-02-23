"""Обработчики корзины."""

from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.cart import cart_keyboard, empty_cart_keyboard
from bot.states.checkout import CheckoutState
from shop.models import Product

router = Router(name='cart')

_EMPTY_CART = 'Ваша корзина пуста.'
_PRODUCT_ADDED = '✅ Товар добавлен в корзину!'
_PRODUCT_NOT_FOUND = 'Товар не найден.'
_CART_CLEARED = '🗑 Корзина очищена.'
_CART_KEY = 'cart'


def _get_cart(data: dict[str, Any]) -> dict[str, Any]:
    """Получить корзину из данных FSM."""
    cart: dict[str, Any] = data.get(_CART_KEY, {})
    return cart


def _cart_total(cart: dict[str, Any]) -> Decimal:
    """Посчитать итоговую сумму корзины."""
    total = Decimal('0')
    for item in cart.values():
        total += Decimal(item['price']) * item['qty']
    return total


def _cart_text(cart: dict[str, Any]) -> str:
    """Текст корзины."""
    lines = ['<b>Ваша корзина:</b>\n']
    for item in cart.values():
        total = Decimal(item['price']) * item['qty']
        lines.append(f'• {item["name"]} × {item["qty"]} = {total} ₽')
    lines.append(f'\n<b>Итого: {_cart_total(cart)} ₽</b>')
    return '\n'.join(lines)


@router.message(Command('cart'))
async def on_cart(message: Message, state: FSMContext) -> None:
    """Показать содержимое корзины."""
    data = await state.get_data()
    cart = _get_cart(data)
    if not cart:
        await message.answer(_EMPTY_CART, reply_markup=empty_cart_keyboard())
        return
    await message.answer(
        _cart_text(cart),
        reply_markup=cart_keyboard(cart),
        parse_mode='HTML',
    )


@router.callback_query(F.data.startswith('cart:add:'))
async def on_cart_add(callback: CallbackQuery, state: FSMContext) -> None:
    """Добавление товара в корзину."""
    if not callback.data:
        return
    product_id = callback.data.split(':')[2]
    try:
        product = await Product.objects.aget(
            id=int(product_id), is_active=True
        )
    except Product.DoesNotExist:
        await callback.answer(_PRODUCT_NOT_FOUND, show_alert=True)
        return

    data = await state.get_data()
    cart = _get_cart(data)

    if product_id in cart:
        cart[product_id]['qty'] += 1
    else:
        cart[product_id] = {
            'name': product.name,
            'qty': 1,
            'price': str(product.price),
        }

    await state.update_data(cart=cart)
    await callback.answer(_PRODUCT_ADDED)


@router.callback_query(F.data.startswith('cart:increase:'))
async def on_cart_increase(callback: CallbackQuery, state: FSMContext) -> None:
    """Увеличить количество товара в корзине."""
    msg = callback.message
    if not callback.data or not isinstance(msg, Message):
        return
    product_id = callback.data.split(':')[2]
    data = await state.get_data()
    cart = _get_cart(data)

    if product_id in cart:
        cart[product_id]['qty'] += 1
        await state.update_data(cart=cart)
        await msg.edit_text(
            _cart_text(cart),
            reply_markup=cart_keyboard(cart),
            parse_mode='HTML',
        )
    await callback.answer()


@router.callback_query(F.data.startswith('cart:decrease:'))
async def on_cart_decrease(callback: CallbackQuery, state: FSMContext) -> None:
    """Уменьшение количества товара."""
    msg = callback.message
    if not callback.data or not isinstance(msg, Message):
        return
    product_id = callback.data.split(':')[2]
    data = await state.get_data()
    cart = _get_cart(data)

    if product_id in cart:
        cart[product_id]['qty'] -= 1
        if cart[product_id]['qty'] <= 0:
            del cart[product_id]
        await state.update_data(cart=cart)

    if not cart:
        await msg.edit_text(_EMPTY_CART, reply_markup=empty_cart_keyboard())
    else:
        await msg.edit_text(
            _cart_text(cart),
            reply_markup=cart_keyboard(cart),
            parse_mode='HTML',
        )
    await callback.answer()


@router.callback_query(F.data.startswith('cart:remove:'))
async def on_cart_remove(callback: CallbackQuery, state: FSMContext) -> None:
    """Удалить товар из корзины."""
    msg = callback.message
    if not callback.data or not isinstance(msg, Message):
        return
    product_id = callback.data.split(':')[2]
    data = await state.get_data()
    cart = _get_cart(data)
    cart.pop(product_id, None)
    await state.update_data(cart=cart)

    if not cart:
        await msg.edit_text(_EMPTY_CART, reply_markup=empty_cart_keyboard())
    else:
        await msg.edit_text(
            _cart_text(cart),
            reply_markup=cart_keyboard(cart),
            parse_mode='HTML',
        )
    await callback.answer()


@router.callback_query(F.data == 'cart:clear')
async def on_cart_clear(callback: CallbackQuery, state: FSMContext) -> None:
    """Очистить корзину полностью."""
    msg = callback.message
    if not isinstance(msg, Message):
        return
    await state.update_data(cart={})
    await msg.edit_text(_CART_CLEARED, reply_markup=empty_cart_keyboard())
    await callback.answer()


@router.callback_query(F.data == 'cart:checkout')
async def on_cart_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало оформления заказа."""
    msg = callback.message
    if not isinstance(msg, Message):
        return
    data = await state.get_data()
    cart = _get_cart(data)

    if not cart:
        await callback.answer(_EMPTY_CART, show_alert=True)
        return

    await state.set_state(CheckoutState.waiting_name)
    await msg.answer('Для оформления заказа введите ваше имя:')
    await callback.answer()


@router.callback_query(F.data == 'cart:noop')
async def on_cart_noop(callback: CallbackQuery) -> None:
    """Заглушка кнопки количества."""
    await callback.answer()
