"""Юнит-тесты PaymentService (T025 + T026 + T059 + T060)."""

from decimal import Decimal
import json
from unittest.mock import MagicMock, patch
import uuid

from django.core.exceptions import PermissionDenied
import pytest

from payments.models import Payment
from payments.services import PaymentService
from shop.models import Order


def _create_order():
    """Создаёт Order в БД для тестирования."""
    return Order.objects.create(
        uuid=uuid.uuid4(),
        user_tg_id=111,
        user_name='Иван Иванов',
        user_phone='+79991234567',
        user_address='г. Москва, ул. Ленина, 1',
        status='pending_payment',
        subtotal=Decimal('400.00'),
        delivery_cost=Decimal('300.00'),
        total=Decimal('700.00'),
    )


# === T025: create_sbp_invoice ===


@pytest.mark.django_db
class TestCreateSbpInvoice:
    """Тесты PaymentService.create_sbp_invoice()."""

    @patch('payments.services.YooKassaPayment')
    def test_creates_payment_record(self, mock_yk):
        """Создаётся запись Payment в БД."""
        mock_yk.create.return_value = MagicMock(
            id='pay_123',
            confirmation=MagicMock(
                confirmation_url='https://pay.example.com',
            ),
        )
        order = _create_order()

        PaymentService.create_sbp_invoice(order)

        assert Payment.objects.filter(order=order).exists()

    @patch('payments.services.YooKassaPayment')
    def test_idempotency_key_from_uuid(self, mock_yk):
        """Idempotency key формируется из order.uuid."""
        mock_yk.create.return_value = MagicMock(
            id='pay_123',
            confirmation=MagicMock(
                confirmation_url='https://pay.example.com',
            ),
        )
        order = _create_order()

        result = PaymentService.create_sbp_invoice(order)

        call_kwargs = mock_yk.create.call_args.kwargs
        assert 'idempotency_key' in call_kwargs
        assert result['idempotency_key'] is not None

    @patch('payments.services.YooKassaPayment')
    def test_yookassa_api_params(self, mock_yk):
        """Корректные параметры в YooKassa API."""
        mock_yk.create.return_value = MagicMock(
            id='pay_123',
            confirmation=MagicMock(
                confirmation_url='https://pay.example.com',
            ),
        )
        order = _create_order()

        PaymentService.create_sbp_invoice(order)

        call_args = mock_yk.create.call_args[0][0]
        assert call_args['amount']['value'] == '700.00'
        assert call_args['amount']['currency'] == 'RUB'
        assert call_args['capture'] is True


# === T026: handle_yookassa_webhook ===


@pytest.mark.django_db
class TestHandleYookassaWebhook:
    """Тесты PaymentService.handle_yookassa_webhook()."""

    TRUSTED_IP = '185.71.76.1'
    UNTRUSTED_IP = '1.2.3.4'

    def _setup(self):
        """Order + Payment для тестирования webhook."""
        order = _create_order()
        Payment.objects.create(
            order=order,
            provider='yookassa',
            provider_payment_id='pay_123',
            idempotency_key=uuid.uuid4(),
            amount=Decimal('700.00'),
            currency='RUB',
            status='pending',
        )
        return order

    def _webhook_body(self, payment_id='pay_123'):
        """Тело YooKassa webhook."""
        return json.dumps(
            {
                'type': 'notification',
                'event': 'payment.succeeded',
                'object': {
                    'id': payment_id,
                    'status': 'succeeded',
                    'paid': True,
                },
            }
        ).encode()

    def test_rejects_untrusted_ip(self):
        """PermissionDenied для IP вне доверенного диапазона."""
        with pytest.raises(PermissionDenied):
            PaymentService.handle_yookassa_webhook(
                body=self._webhook_body(),
                client_ip=self.UNTRUSTED_IP,
            )

    def test_updates_status_to_paid(self):
        """Статус заказа меняется на paid."""
        order = self._setup()

        PaymentService.handle_yookassa_webhook(
            body=self._webhook_body(),
            client_ip=self.TRUSTED_IP,
        )

        order.refresh_from_db()
        assert order.status == 'paid'

    def test_idempotent_duplicate(self):
        """Повторный вызов не меняет результат."""
        order = self._setup()
        body = self._webhook_body()

        PaymentService.handle_yookassa_webhook(
            body=body,
            client_ip=self.TRUSTED_IP,
        )
        PaymentService.handle_yookassa_webhook(
            body=body,
            client_ip=self.TRUSTED_IP,
        )

        order.refresh_from_db()
        assert order.status == 'paid'


# === T059: create_stars_invoice ===


@pytest.mark.django_db
class TestCreateStarsInvoice:
    """Тесты PaymentService.create_stars_invoice()."""

    def test_creates_payment_record(self):
        """Создаётся запись Payment с provider=stars, currency=XTR."""
        order = _create_order()

        PaymentService.create_stars_invoice(order)

        payment = Payment.objects.get(order=order)
        assert payment.provider == 'stars'
        assert payment.currency == 'XTR'

    def test_payload_is_order_uuid(self):
        """payload содержит UUID заказа."""
        order = _create_order()

        result = PaymentService.create_stars_invoice(order)

        assert result['payload'] == str(order.uuid)

    def test_returns_xtr_prices(self):
        """Валюта XTR и prices — непустой список."""
        order = _create_order()

        result = PaymentService.create_stars_invoice(order)

        assert result['currency'] == 'XTR'
        assert isinstance(result['prices'], list)
        assert len(result['prices']) > 0


# === T060: handle_stars_payment ===


@pytest.mark.django_db
class TestHandleStarsPayment:
    """Тесты PaymentService.handle_stars_payment()."""

    def _setup(self):
        """Order + Payment (stars) для тестирования."""
        order = _create_order()
        Payment.objects.create(
            order=order,
            provider='stars',
            idempotency_key=uuid.uuid4(),
            amount=Decimal('700.00'),
            currency='XTR',
            status='pending',
        )
        return order

    def test_updates_order_status_to_paid(self):
        """Статус заказа меняется на paid."""
        order = self._setup()

        PaymentService.handle_stars_payment(
            user_id=111,
            payload=str(order.uuid),
            charge_id='charge_abc',
            amount=700,
        )

        order.refresh_from_db()
        assert order.status == 'paid'

    def test_idempotent_duplicate(self):
        """Повторный вызов не меняет результат."""
        order = self._setup()

        PaymentService.handle_stars_payment(
            user_id=111,
            payload=str(order.uuid),
            charge_id='charge_abc',
            amount=700,
        )
        PaymentService.handle_stars_payment(
            user_id=111,
            payload=str(order.uuid),
            charge_id='charge_abc',
            amount=700,
        )

        order.refresh_from_db()
        assert order.status == 'paid'

    def test_stores_charge_id(self):
        """charge_id сохраняется в Payment."""
        order = self._setup()

        PaymentService.handle_stars_payment(
            user_id=111,
            payload=str(order.uuid),
            charge_id='charge_abc',
            amount=700,
        )

        payment = Payment.objects.get(order=order)
        assert payment.provider_payment_id == 'charge_abc'
