"""Инлайн-клавиатуры каталога: категории, товары, карточка товара."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def categories_keyboard(
    categories: list,
) -> InlineKeyboardMarkup:
    """Клавиатура со списком активных категорий.

    Каждая категория — отдельная строка.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=cat.name,
                callback_data=f'category:list:{cat.id}',
            )
        ]
        for cat in categories
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_keyboard(
    products: list,
    category_id: int,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Клавиатура со списком товаров категории с пагинацией.

    Каждый товар — отдельная строка (название + цена).
    Внизу — кнопки «Пред.» / «След.» при наличии страниц.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=f'{p.name} — {p.price} ₽',
                callback_data=f'product:view:{p.id}',
            )
        ]
        for p in products
    ]

    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text='◀ Пред.',
                callback_data=f'category:page:{category_id}:{page - 1}',
            )
        )
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(
                text='След. ▶',
                callback_data=f'category:page:{category_id}:{page + 1}',
            )
        )
    if nav:
        buttons.append(nav)

    buttons.append(
        [
            InlineKeyboardButton(
                text='◀ К категориям',
                callback_data='category:list:0',
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_card_keyboard(
    product_id: int,
    category_id: int,
) -> InlineKeyboardMarkup:
    """Клавиатура карточки товара.

    Кнопки: «Добавить в корзину» и «Назад к категории».
    """
    buttons = [
        [
            InlineKeyboardButton(
                text='🛒 Добавить в корзину',
                callback_data=f'cart:add:{product_id}',
            )
        ],
        [
            InlineKeyboardButton(
                text='◀ Назад',
                callback_data=f'category:list:{category_id}',
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
