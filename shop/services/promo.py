"""Сервис валидации и применения промокодов."""

from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
import structlog

from shop.models import (
    DISCOUNT_FREE_DELIVERY,
    DISCOUNT_PERCENTAGE,
    Order,
    PromoCode,
    PromoCodeUsage,
)

logger = structlog.get_logger(__name__)


class PromoService:
    """Операции с промокодами."""

    @staticmethod
    @transaction.atomic
    def validate_code(
        *, code: str, user_tg_id: int, subtotal: Decimal
    ) -> PromoCode | None:
        """Валидация промокода."""
        try:
            promo = PromoCode.objects.select_for_update().get(
                code=code.upper(),
                is_active=True,
            )
        except PromoCode.DoesNotExist:
            return None

        if promo.expires_at and promo.expires_at < timezone.now():
            return None

        if promo.max_uses is not None and promo.used_count >= promo.max_uses:
            return None

        user_usage_count = PromoCodeUsage.objects.filter(
            promo_code=promo,
            user_tg_id=user_tg_id,
        ).count()
        if user_usage_count >= promo.max_uses_per_user:
            return None

        if subtotal < promo.min_order_amount:
            return None

        return promo

    @staticmethod
    def apply_discount(
        *, subtotal: Decimal, delivery_cost: Decimal, promo: PromoCode
    ) -> tuple[Decimal, Decimal]:
        """Расчёт скидки по промокоду."""
        if promo.discount_type == DISCOUNT_PERCENTAGE:
            discount_amount = subtotal * promo.discount_value / Decimal('100')
            return discount_amount, delivery_cost

        if promo.discount_type == DISCOUNT_FREE_DELIVERY:
            return Decimal('0'), Decimal('0')

        return Decimal('0'), delivery_cost

    @staticmethod
    @transaction.atomic
    def record_usage(
        *, promo: PromoCode, user_tg_id: int, order: Order
    ) -> None:
        """Запись использования промокода."""
        PromoCodeUsage.objects.create(
            promo_code=promo,
            user_tg_id=user_tg_id,
            order=order,
        )
        PromoCode.objects.filter(pk=promo.pk).update(
            used_count=F('used_count') + 1,
        )
        logger.info(
            'promo_code_used',
            code=promo.code,
            user_tg_id=user_tg_id,
            order_id=order.id,
        )
