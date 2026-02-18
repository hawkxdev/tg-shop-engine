"""Обработчики команд /start и /help."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router(name='start')

_WELCOME = (
    'Добро пожаловать в магазин!\n\n'
    'Используйте /catalog для просмотра товаров\n'
    'или /help для списка команд.'
)

_HELP = (
    '<b>Доступные команды:</b>\n\n'
    '/start — начать работу с ботом\n'
    '/catalog — каталог товаров\n'
    '/cart — корзина\n'
    '/status — статус заказа\n'
    '/help — список команд'
)


@router.message(CommandStart())
async def on_start(message: Message, state: FSMContext) -> None:
    """Приветствие и сброс FSM-состояния."""
    await state.clear()
    await message.answer(_WELCOME)


@router.message(Command('help'))
async def on_help(message: Message) -> None:
    """Список доступных команд."""
    await message.answer(_HELP)
