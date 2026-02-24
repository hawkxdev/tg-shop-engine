"""Сервис платежей (YooKassa + Telegram Stars)."""

import json
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
import structlog
from yookassa import Payment as YooKassaPayment

from payments.models import (
    PAYMENT_STATUS_CANCELED,
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_SUCCEEDED,
    Payment,
)
from shop.models import ORDER_STATUS_PAID, Order

logger = structlog.get_logger(__name__)

_DEFAULT_YOOKASSA_IPS = [
    '185.71.76.0',
    '185.71.76.1',
    '185.71.77.0',
    '185.71.77.1',
]

_TRUSTED_IPS: frozenset[str] = frozenset(
    getattr(settings, 'YOOKASSA_TRUSTED_IPS', _DEFAULT_YOOKASSA_IPS)
)


def _build_yookassa_payload(order: Order) -> dict[str, Any]:
    """Формирование payload для YooKassa API."""
    return {
        'amount': {
            'value': str(order.total),
            'currency': 'RUB',
        },
        'capture': True,
        'confirmation': {
            'type': 'redirect',
            'return_url': settings.WEBHOOK_URL,
        },
        'description': f'Заказ {order.uuid}',
    }


class PaymentService:
    """Операции с платежами."""

    @staticmethod
    def create_sbp_invoice(order: Order) -> dict[str, Any]:
        """Создание счёта СБП."""
        idempotency_key = str(order.uuid)

        response = YooKassaPayment.create(
            _build_yookassa_payload(order),
            idempotency_key=idempotency_key,
        )

        Payment.objects.create(
            order=order,
            provider='yookassa',
            provider_payment_id=response.id,
            idempotency_key=str(order.uuid),
            amount=order.total,
            currency='RUB',
            status=PAYMENT_STATUS_PENDING,
        )

        logger.info(
            'sbp_invoice_created',
            order_id=order.id,
            payment_id=response.id,
        )
        confirmation_url = (
            response.confirmation.confirmation_url
            if response.confirmation
            else ''
        )
        return {
            'payment_id': response.id,
            'confirmation_url': confirmation_url,
            'idempotency_key': idempotency_key,
        }

    @staticmethod
    def create_stars_invoice(order: Order) -> dict[str, Any]:
        """Создание инвойса Stars."""
        Payment.objects.create(
            order=order,
            provider='stars',
            idempotency_key=str(order.uuid),
            amount=order.total,
            currency='XTR',
            status=PAYMENT_STATUS_PENDING,
        )

        logger.info('stars_invoice_created', order_id=order.id)
        return {
            'title': f'Заказ #{order.id}',
            'payload': str(order.uuid),
            'currency': 'XTR',
            'prices': [
                {
                    'label': f'Заказ #{order.id}',
                    'amount': int(order.total),
                },
            ],
        }

    @staticmethod
    @transaction.atomic
    def handle_yookassa_webhook(*, body: bytes, client_ip: str) -> None:
        """Обработка webhook YooKassa."""
        if client_ip not in _TRUSTED_IPS:
            raise PermissionDenied(f'Недоверенный IP: {client_ip}')

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise PermissionDenied('Invalid JSON payload') from None

        if data.get('event') != 'payment.succeeded':
            return

        payment_obj = data.get('object', {})
        provider_payment_id = payment_obj.get('id')
        if not provider_payment_id:
            raise PermissionDenied('Missing payment ID in payload')

        payment = Payment.objects.select_for_update().get(
            provider_payment_id=provider_payment_id
        )

        _TERMINAL = {PAYMENT_STATUS_SUCCEEDED, PAYMENT_STATUS_CANCELED}
        if payment.status in _TERMINAL:
            return

        payment.status = PAYMENT_STATUS_SUCCEEDED
        payment.provider_data = payment_obj
        payment.save(
            update_fields=[
                'status',
                'provider_data',
                'updated_at',
            ]
        )

        order = payment.order
        order.status = ORDER_STATUS_PAID
        order.save(update_fields=['status', 'updated_at'])
        logger.info(
            'yookassa_webhook_processed',
            order_id=order.id,
            provider_payment_id=provider_payment_id,
        )

        logger.warning(
            'notification_skipped',
            order_id=order.id,
            reason='sync_context_no_bot',
        )

    @staticmethod
    @transaction.atomic
    def handle_stars_payment(
        *, user_id: int, payload: str, charge_id: str, amount: int
    ) -> None:
        """Обработка платежа Stars."""
        order = Order.objects.select_for_update().get(uuid=payload)

        if order.status == ORDER_STATUS_PAID:
            return

        payment = Payment.objects.select_for_update().get(
            order=order, provider='stars'
        )

        payment.status = PAYMENT_STATUS_SUCCEEDED
        payment.provider_payment_id = charge_id
        payment.provider_data = {
            'charge_id': charge_id,
            'user_id': user_id,
            'amount': amount,
        }
        payment.save(
            update_fields=[
                'status',
                'provider_payment_id',
                'provider_data',
                'updated_at',
            ]
        )

        order.status = ORDER_STATUS_PAID
        order.save(update_fields=['status', 'updated_at'])
        logger.info(
            'stars_payment_processed',
            order_id=order.id,
            charge_id=charge_id,
            amount=amount,
        )
