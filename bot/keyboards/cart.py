"""Клавиатуры корзины."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def cart_keyboard(cart_items: dict) -> InlineKeyboardMarkup:
    """Клавиатура корзины с товарами."""
    buttons = []
    for product_id, item in cart_items.items():
        name = item['name']
        qty = item['qty']
        price = item['price']
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f'{name} — {price} ₽',
                    callback_data=f'product:view:{product_id}',
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text='−',
                    callback_data=f'cart:decrease:{product_id}',
                ),
                InlineKeyboardButton(
                    text=str(qty),
                    callback_data='cart:noop',
                ),
                InlineKeyboardButton(
                    text='+',
                    callback_data=f'cart:increase:{product_id}',
                ),
                InlineKeyboardButton(
                    text='✕',
                    callback_data=f'cart:remove:{product_id}',
                ),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text='🗑 Очистить корзину',
                callback_data='cart:clear',
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text='✅ Оформить заказ',
                callback_data='cart:checkout',
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def empty_cart_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура пустой корзины."""
    buttons = [
        [
            InlineKeyboardButton(
                text='🛍 Перейти в каталог',
                callback_data='category:list:0',
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
