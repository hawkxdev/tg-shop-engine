"""Сервис валидации и применения промокодов."""

from decimal import Decimal

from django.db.models import F
from django.utils import timezone
import structlog

from shop.models import Order, PromoCode, PromoCodeUsage

logger = structlog.get_logger(__name__)


class PromoService:
    """Операции с промокодами."""

    @staticmethod
    def validate_code(
        *, code: str, user_tg_id: int, subtotal: Decimal
    ) -> PromoCode | None:
        """Валидация промокода по 5 правилам.

        Args:
            code: Строка промокода.
            user_tg_id: Telegram ID покупателя.
            subtotal: Сумма заказа до скидки.

        Returns:
            PromoCode если валиден, иначе None.
        """
        try:
            promo = PromoCode.objects.get(
                code=code.upper(),
                is_active=True,
            )
        except PromoCode.DoesNotExist:
            return None

        # Проверка срока действия
        if promo.expires_at and promo.expires_at < timezone.now():
            return None

        # Проверка общего лимита использований
        if promo.max_uses is not None and promo.used_count >= promo.max_uses:
            return None

        # Проверка лимита на пользователя
        user_usage_count = PromoCodeUsage.objects.filter(
            promo_code=promo,
            user_tg_id=user_tg_id,
        ).count()
        if user_usage_count >= promo.max_uses_per_user:
            return None

        # Проверка минимальной суммы заказа
        if subtotal < promo.min_order_amount:
            return None

        return promo

    @staticmethod
    def apply_discount(
        *, subtotal: Decimal, delivery_cost: Decimal, promo: PromoCode
    ) -> tuple[Decimal, Decimal]:
        """Расчёт скидки по типу промокода.

        Args:
            subtotal: Сумма заказа до скидки.
            delivery_cost: Стоимость доставки.
            promo: Объект PromoCode.

        Returns:
            Кортеж (discount_amount, new_delivery_cost).
        """
        if promo.discount_type == 'percentage':
            discount_amount = subtotal * promo.discount_value / Decimal('100')
            return discount_amount, delivery_cost

        if promo.discount_type == 'free_delivery':
            return Decimal('0'), Decimal('0')

        return Decimal('0'), delivery_cost

    @staticmethod
    def record_usage(*, promo: PromoCode, user_tg_id: int, order: Order) -> None:
        """Запись использования промокода.

        Создаёт PromoCodeUsage и атомарно увеличивает
        used_count через F().

        Args:
            promo: Объект PromoCode.
            user_tg_id: Telegram ID покупателя.
            order: Объект Order.
        """
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
