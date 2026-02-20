"""Инлайн-клавиатуры для процесса оформления заказа."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def address_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения нормализованного адреса."""
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
    """Клавиатура шага промокода (пропустить / отмена)."""
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
    """Клавиатура подтверждения заказа (подтвердить / отмена)."""
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
    """Клавиатура выбора способа оплаты (СБП / Telegram Stars)."""
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
    """Кнопка отмены оформления заказа (доступна на каждом шаге)."""
    buttons = [
        [
            InlineKeyboardButton(
                text='❌ Отмена',
                callback_data='checkout:cancel',
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
