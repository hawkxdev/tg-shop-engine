"""Сервис платежей (YooKassa + Telegram Stars)."""

import json
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from yookassa import Payment as YooKassaPayment

from payments.models import Payment

logger = logging.getLogger(__name__)

# Доверенные IP-адреса YooKassa
# https://yookassa.ru/developers/using-api/webhooks
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
    def create_sbp_invoice(order):
        """Создание счёта СБП через YooKassa.

        Args:
            order: Order с uuid и total.

        Returns:
            dict с payment_id, confirmation_url,
            idempotency_key.
        """
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

        return {
            'payment_id': response.id,
            'confirmation_url': (response.confirmation.confirmation_url),
            'idempotency_key': idempotency_key,
        }

    @staticmethod
    @transaction.atomic
    def handle_yookassa_webhook(*, body, client_ip):
        """Обработка webhook от YooKassa.

        Args:
            body: Тело запроса (bytes).
            client_ip: IP клиента.

        Raises:
            PermissionDenied: IP не в доверенном списке.
        """
        if client_ip not in _TRUSTED_IPS:
            raise PermissionDenied(f'Недоверенный IP: {client_ip}')

        data = json.loads(body)
        payment_obj = data['object']
        provider_payment_id = payment_obj['id']

        payment = Payment.objects.select_for_update().get(
            provider_payment_id=provider_payment_id
        )

        # Идемпотентность: если уже обработан — пропускаем
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
