"""Юнит-тесты PromoService."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
import pytest

from shop.services.promo import PromoService
from tests.factories import (
    OrderFactory,
    PromoCodeFactory,
    PromoCodeUsageFactory,
)

# --- T050: validate_code() ---


@pytest.mark.django_db
class TestValidateCode:
    """Тесты PromoService.validate_code()."""

    def test_valid_code(self):
        """Валидный промокод возвращает объект PromoCode."""
        promo = PromoCodeFactory(
            code='SALE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('0'),
            max_uses=100,
            max_uses_per_user=1,
            used_count=0,
            is_active=True,
            expires_at=timezone.now() + timedelta(days=30),
        )

        result = PromoService.validate_code(
            code='SALE10',
            user_tg_id=111,
            subtotal=Decimal('2000.00'),
        )

        assert result is not None
        assert result.pk == promo.pk

    def test_nonexistent_code_returns_none(self):
        """Несуществующий код возвращает None."""
        result = PromoService.validate_code(
            code='DOESNOTEXIST',
            user_tg_id=111,
            subtotal=Decimal('2000.00'),
        )

        assert result is None

    def test_inactive_code_returns_none(self):
        """Неактивный промокод (is_active=False) возвращает None."""
        PromoCodeFactory(code='INACTIVE', is_active=False)

        result = PromoService.validate_code(
            code='INACTIVE',
            user_tg_id=111,
            subtotal=Decimal('2000.00'),
        )

        assert result is None

    def test_expired_code_returns_none(self):
        """Истёкший промокод возвращает None."""
        PromoCodeFactory(
            code='EXPIRED',
            expires_at=timezone.now() - timedelta(days=1),
        )

        result = PromoService.validate_code(
            code='EXPIRED',
            user_tg_id=111,
            subtotal=Decimal('2000.00'),
        )

        assert result is None

    def test_usage_limit_reached_returns_none(self):
        """Промокод с исчерпанным лимитом использований."""
        PromoCodeFactory(
            code='MAXED',
            max_uses=100,
            used_count=100,
        )

        result = PromoService.validate_code(
            code='MAXED',
            user_tg_id=111,
            subtotal=Decimal('2000.00'),
        )

        assert result is None

    def test_per_user_limit_reached_returns_none(self):
        """Промокод с исчерпанным лимитом на пользователя."""
        promo = PromoCodeFactory(
            code='ONCE',
            max_uses_per_user=1,
        )
        PromoCodeUsageFactory(
            promo_code=promo,
            user_tg_id=111,
        )

        result = PromoService.validate_code(
            code='ONCE',
            user_tg_id=111,
            subtotal=Decimal('2000.00'),
        )

        assert result is None

    def test_min_order_not_met_returns_none(self):
        """Промокод с минимальной суммой больше subtotal."""
        PromoCodeFactory(
            code='BIGORDER',
            min_order_amount=Decimal('3000.00'),
        )

        result = PromoService.validate_code(
            code='BIGORDER',
            user_tg_id=111,
            subtotal=Decimal('2000.00'),
        )

        assert result is None


# --- T051: apply_discount() ---


@pytest.mark.django_db
class TestApplyDiscount:
    """Тесты PromoService.apply_discount()."""

    def test_percentage_discount(self):
        """Процентная скидка: 10% от 2000 = 200."""
        promo = PromoCodeFactory(
            discount_type='percentage',
            discount_value=Decimal('10.00'),
        )

        discount_amount, new_delivery = PromoService.apply_discount(
            subtotal=Decimal('2000.00'),
            delivery_cost=Decimal('300.00'),
            promo=promo,
        )

        assert discount_amount == Decimal('200.00')
        assert new_delivery == Decimal('300.00')

    def test_free_delivery(self):
        """Бесплатная доставка: delivery_cost = 0."""
        promo = PromoCodeFactory(
            discount_type='free_delivery',
            discount_value=Decimal('0'),
        )

        discount_amount, new_delivery = PromoService.apply_discount(
            subtotal=Decimal('2000.00'),
            delivery_cost=Decimal('300.00'),
            promo=promo,
        )

        assert discount_amount == Decimal('0')
        assert new_delivery == Decimal('0')


# --- T052: record_usage() ---


@pytest.mark.django_db
class TestRecordUsage:
    """Тесты PromoService.record_usage()."""

    def test_creates_usage_record(self):
        """Создаёт запись PromoCodeUsage."""
        from shop.models import PromoCodeUsage

        promo = PromoCodeFactory(code='TRACK')
        order = OrderFactory()

        PromoService.record_usage(
            promo=promo,
            user_tg_id=111,
            order=order,
        )

        usage = PromoCodeUsage.objects.get(
            promo_code=promo,
            order=order,
        )
        assert usage.user_tg_id == 111

    def test_increments_used_count_atomically(self):
        """used_count увеличивается атомарно через F()."""
        promo = PromoCodeFactory(code='ATOMIC', used_count=5)
        order = OrderFactory()

        PromoService.record_usage(
            promo=promo,
            user_tg_id=111,
            order=order,
        )

        promo.refresh_from_db()
        assert promo.used_count == 6
