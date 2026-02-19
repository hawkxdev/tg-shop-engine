"""Модели платежей."""

import uuid

from django.db import models

PAYMENT_PROVIDER_CHOICES = [
    ('yookassa', 'YooKassa'),
    ('stars', 'Telegram Stars'),
]

PAYMENT_STATUS_CHOICES = [
    ('pending', 'Ожидает'),
    ('succeeded', 'Успешно'),
    ('canceled', 'Отменён'),
]


class Payment(models.Model):
    """Запись о платеже (YooKassa или Telegram Stars)."""

    order = models.ForeignKey(
        'shop.Order',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    provider = models.CharField(
        max_length=10,
        choices=PAYMENT_PROVIDER_CHOICES,
    )
    provider_payment_id = models.CharField(
        max_length=100, blank=True, null=True
    )
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
    )
    provider_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['provider_payment_id'],
                name='pay_provider_id',
            ),
        ]

    def __str__(self):
        return f'Платёж {self.idempotency_key} ({self.get_status_display()})'
