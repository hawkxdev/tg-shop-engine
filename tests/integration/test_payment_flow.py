"""Интеграционный тест Stars payment flow (T061)."""

from decimal import Decimal
import uuid

import pytest

from payments.models import Payment
from payments.services import PaymentService
from shop.models import Order


def _create_order():
    """Создаёт Order в БД для тестирования."""
    return Order.objects.create(
        uuid=uuid.uuid4(),
        user_tg_id=222,
        user_name='Пётр Петров',
        user_phone='+79997654321',
        user_address='г. Санкт-Петербург, Невский пр., 1',
        status='pending_payment',
        subtotal=Decimal('500.00'),
        delivery_cost=Decimal('300.00'),
        total=Decimal('800.00'),
    )


@pytest.mark.django_db
class TestStarsPaymentFlow:
    """Полный цикл: Order → Stars invoice → payment → paid."""

    def test_full_stars_payment_flow(self):
        """checkout → create_stars_invoice → handle_stars_payment → paid."""
        # 1. Создаём заказ
        order = _create_order()

        # 2. Создаём Stars invoice
        invoice = PaymentService.create_stars_invoice(order)
        assert invoice['currency'] == 'XTR'
        assert invoice['payload'] == str(order.uuid)

        # Payment record создан
        payment = Payment.objects.get(order=order)
        assert payment.provider == 'stars'
        assert payment.status == 'pending'

        # 3. Имитируем successful_payment от Telegram
        PaymentService.handle_stars_payment(
            user_id=order.user_tg_id,
            payload=invoice['payload'],
            charge_id='tg_charge_xyz',
            amount=800,
        )

        # 4. Проверяем финальное состояние
        order.refresh_from_db()
        assert order.status == 'paid'

        payment.refresh_from_db()
        assert payment.status == 'succeeded'
        assert payment.provider_payment_id == 'tg_charge_xyz'
