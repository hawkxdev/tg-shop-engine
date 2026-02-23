"""Обработчики каталога."""

import contextlib
import math

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.keyboards.catalog import (
    categories_keyboard,
    product_card_keyboard,
    products_keyboard,
)
from shop.models import Category, Product

router = Router(name='catalog')

_PAGE_SIZE = 8
_NO_CATEGORIES = 'Каталог пока пуст.'
_NO_PRODUCTS = 'В этой категории нет товаров.'


@router.message(Command('catalog'))
async def on_catalog(message: Message) -> None:
    """Показать список активных категорий."""
    categories = [
        c
        async for c in Category.objects.filter(is_active=True).order_by('name')
    ]
    if not categories:
        await message.answer(_NO_CATEGORIES)
        return
    await message.answer(
        'Выберите категорию:',
        reply_markup=categories_keyboard(categories),
    )


@router.callback_query(F.data.startswith('category:list:'))
async def on_category_list(callback: CallbackQuery) -> None:
    """Навигация по категориям."""
    msg = callback.message
    if not callback.data or not isinstance(msg, Message):
        return
    category_id = int(callback.data.split(':')[2])
    if category_id == 0:
        categories = [
            c
            async for c in Category.objects.filter(is_active=True).order_by(
                'name'
            )
        ]
        await msg.edit_text(
            'Выберите категорию:',
            reply_markup=categories_keyboard(categories),
        )
        await callback.answer()
        return

    await _show_products(callback, category_id, page=1)


@router.callback_query(F.data.startswith('category:page:'))
async def on_category_page(callback: CallbackQuery) -> None:
    """Показать товары категории на заданной странице."""
    if not callback.data:
        return
    _, _, category_id_str, page_str = callback.data.split(':')
    await _show_products(callback, int(category_id_str), int(page_str))


@router.callback_query(F.data.startswith('product:view:'))
async def on_product_view(callback: CallbackQuery) -> None:
    """Показать карточку товара с изображением."""
    msg = callback.message
    if not callback.data or not isinstance(msg, Message):
        return
    product_id = int(callback.data.split(':')[2])
    try:
        product = await Product.objects.select_related('category').aget(
            id=product_id, is_active=True
        )
    except Product.DoesNotExist:
        await callback.answer('Товар не найден.', show_alert=True)
        return

    text = (
        f'<b>{product.name}</b>\n\n'
        f'{product.description}\n\n'
        f'Цена: <b>{product.price} ₽</b>\n'
        f'Остаток: {product.stock} шт.'
    )
    keyboard = product_card_keyboard(product.id, product.category_id)

    if product.photo:
        photo = FSInputFile(product.photo.path)
        await msg.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=keyboard,
            parse_mode='HTML',
        )
        with contextlib.suppress(Exception):
            await msg.delete()
    else:
        await msg.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


async def _show_products(
    callback: CallbackQuery,
    category_id: int,
    page: int,
) -> None:
    """Отображение товаров категории."""
    msg = callback.message
    if not isinstance(msg, Message):
        return
    try:
        category = await Category.objects.aget(id=category_id, is_active=True)
    except Category.DoesNotExist:
        await callback.answer('Категория не найдена.', show_alert=True)
        return

    total = await Product.objects.filter(
        category=category, is_active=True
    ).acount()
    if total == 0:
        await callback.answer(_NO_PRODUCTS, show_alert=True)
        return

    total_pages = math.ceil(total / _PAGE_SIZE)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * _PAGE_SIZE

    products = [
        p
        async for p in Product.objects.filter(
            category=category, is_active=True
        ).order_by('name')[offset : offset + _PAGE_SIZE]
    ]

    text = f'<b>{category.name}</b>\n\nСтраница {page} из {total_pages}:'
    keyboard = products_keyboard(products, category_id, page, total_pages)
    await msg.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()
