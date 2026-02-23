"""Сервис платежей (YooKassa + Telegram Stars)."""

import json
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
import structlog
from yookassa import Payment as YooKassaPayment

from bot.services.notification import NotificationService
from payments.models import Payment
from shop.models import Order

logger = structlog.get_logger(__name__)

_TRUSTED_IPS = frozenset(
    {
        '185.71.76.0',
        '185.71.76.1',
        '185.71.77.0',
        '185.71.77.1',
    }
)


class PaymentService:
    """Операции с платежами."""

    @staticmethod
    def create_sbp_invoice(order: Order) -> dict[str, Any]:
        """Создание счёта СБП."""
        idempotency_key = str(order.uuid)

        response = YooKassaPayment.create(
            {
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
            },
            idempotency_key=idempotency_key,
        )

        Payment.objects.create(
            order=order,
            provider='yookassa',
            provider_payment_id=response.id,
            idempotency_key=order.uuid,
            amount=order.total,
            currency='RUB',
            status='pending',
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
            idempotency_key=order.uuid,
            amount=order.total,
            currency='XTR',
            status='pending',
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

        data = json.loads(body)
        payment_obj = data['object']
        provider_payment_id = payment_obj['id']

        payment = Payment.objects.select_for_update().get(
            provider_payment_id=provider_payment_id
        )

        if payment.status == 'succeeded':
            return

        payment.status = 'succeeded'
        payment.provider_data = payment_obj
        payment.save(
            update_fields=[
                'status',
                'provider_data',
                'updated_at',
            ]
        )

        order = payment.order
        order.status = 'paid'
        order.save(update_fields=['status', 'updated_at'])
        logger.info(
            'yookassa_webhook_processed',
            order_id=order.id,
            provider_payment_id=provider_payment_id,
        )

        # notify_buyer async из sync: MVP trade-off
        NotificationService.notify_buyer(  # type: ignore[unused-coroutine]
            bot=None,
            user_tg_id=order.user_tg_id,
            order=order,
            event='payment_success',
        )

    @staticmethod
    @transaction.atomic
    def handle_stars_payment(
        *, user_id: int, payload: str, charge_id: str, amount: int
    ) -> None:
        """Обработка платежа Stars."""
        order = Order.objects.select_for_update().get(uuid=payload)

        if order.status == 'paid':
            return

        payment = Payment.objects.select_for_update().get(
            order=order, provider='stars'
        )

        payment.status = 'succeeded'
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

        order.status = 'paid'
        order.save(update_fields=['status', 'updated_at'])
        logger.info(
            'stars_payment_processed',
            order_id=order.id,
            charge_id=charge_id,
            amount=amount,
        )
