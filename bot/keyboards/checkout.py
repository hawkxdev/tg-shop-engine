"""Клавиатуры оформления заказа."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def address_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения адреса."""
    buttons = [
        [
            InlineKeyboardButton(
                text='✅ Верно',
                callback_data='address:confirm',
            ),
            InlineKeyboardButton(
                text='✏ Ввести заново',
                callback_data='address:retry',
            ),
        ],
        [
            InlineKeyboardButton(
                text='❌ Отмена',
                callback_data='checkout:cancel',
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promo_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура промокода."""
    buttons = [
        [
            InlineKeyboardButton(
                text='Пропустить',
                callback_data='promo:skip',
            )
        ],
        [
            InlineKeyboardButton(
                text='❌ Отмена',
                callback_data='checkout:cancel',
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения заказа."""
    buttons = [
        [
            InlineKeyboardButton(
                text='✅ Подтвердить',
                callback_data='order:confirm',
            ),
            InlineKeyboardButton(
                text='❌ Отмена',
                callback_data='order:cancel',
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_method_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора оплаты."""
    buttons = [
        [
            InlineKeyboardButton(
                text='💳 СБП (YooKassa)',
                callback_data=f'pay:sbp:{order_id}',
            )
        ],
        [
            InlineKeyboardButton(
                text='⭐ Telegram Stars',
                callback_data=f'pay:stars:{order_id}',
            )
        ],
        [
            InlineKeyboardButton(
                text='❌ Отмена',
                callback_data='checkout:cancel',
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены оформления."""
    buttons = [
        [
            InlineKeyboardButton(
                text='❌ Отмена',
                callback_data='checkout:cancel',
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
