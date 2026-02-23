"""FSM состояния checkout."""

from aiogram.fsm.state import State, StatesGroup


class CheckoutState(StatesGroup):
    """Шаги оформления заказа."""

    waiting_name = State()
    waiting_phone = State()
    waiting_address = State()
    confirm_address = State()
    waiting_promo = State()
    confirm_order = State()
    waiting_payment = State()
