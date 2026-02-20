"""FSM-группа состояний для процесса оформления заказа."""

from aiogram.fsm.state import State, StatesGroup


class CheckoutState(StatesGroup):
    """Состояния FSM оформления заказа.

    Поток: имя → телефон → адрес → подтверждение адреса →
           промокод → подтверждение заказа → ожидание оплаты.
    """

    waiting_name = State()
    waiting_phone = State()
    waiting_address = State()
    confirm_address = State()
    waiting_promo = State()
    confirm_order = State()
    waiting_payment = State()
