"""Интеграционный тест: обработка YooKassa webhook."""

from decimal import Decimal
import json
from unittest.mock import AsyncMock, patch
import uuid

import pytest

from payments.models import Payment
from payments.services import PaymentService
from shop.models import Order


@pytest.mark.django_db
class TestWebhookProcessing:
    """YooKassa callback → статус заказа → уведомление."""

    TRUSTED_IP = '185.71.76.1'

    def _setup(self):
        """Order (pending_payment) + Payment (pending)."""
        order = Order.objects.create(
            uuid=uuid.uuid4(),
            user_tg_id=111,
            user_name='Иван Иванов',
            user_phone='+79991234567',
            user_address='г. Москва, ул. Ленина, 1',
            status='pending_payment',
            subtotal=Decimal('1300.00'),
            delivery_cost=Decimal('300.00'),
            total=Decimal('1600.00'),
        )
        Payment.objects.create(
            order=order,
            provider='yookassa',
            provider_payment_id='pay_wh_123',
            idempotency_key=uuid.uuid4(),
            amount=Decimal('1600.00'),
            currency='RUB',
            status='pending',
        )
        return order

    def _webhook_body(self, payment_id='pay_wh_123'):
        """Тело YooKassa webhook."""
        return json.dumps(
            {
                'type': 'notification',
                'event': 'payment.succeeded',
                'object': {
                    'id': payment_id,
                    'status': 'succeeded',
                    'paid': True,
                    'amount': {
                        'value': '1600.00',
                        'currency': 'RUB',
                    },
                },
            }
        ).encode()

    def test_updates_order_status(self):
        """Webhook меняет статус заказа на paid."""
        order = self._setup()

        PaymentService.handle_yookassa_webhook(
            body=self._webhook_body(),
            client_ip=self.TRUSTED_IP,
        )

        order.refresh_from_db()
        assert order.status == 'paid'

    @patch('payments.services.NotificationService')
    def test_sends_notification(self, mock_notify_cls):
        """Webhook отправляет уведомление покупателю."""
        self._setup()
        mock_notify_cls.notify_buyer = AsyncMock()

        PaymentService.handle_yookassa_webhook(
            body=self._webhook_body(),
            client_ip=self.TRUSTED_IP,
        )

        mock_notify_cls.notify_buyer.assert_called_once()
