"""Интеграционный тест: полный flow оформления заказа."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from payments.services import PaymentService
from shop.models import OrderItem
from shop.services.address import AddressService
from shop.services.order import OrderService
from tests.factories import ProductFactory


@pytest.mark.django_db
class TestCheckoutFlow:
    """Корзина → нормализация адреса → заказ → ссылка на оплату."""

    @pytest.mark.asyncio
    async def test_cart_to_payment_link(self):
        """Полный flow: товары → заказ → payment link."""
        # 1. Товары в каталоге
        p1 = ProductFactory(price=Decimal('500.00'), stock=10)
        p2 = ProductFactory(price=Decimal('300.00'), stock=5)
        cart_items = {p1.id: 2, p2.id: 1}

        # 2. Нормализация адреса (мок DaData)
        with patch.object(
            AddressService,
            'normalize_address',
            new_callable=AsyncMock,
            return_value={
                'normalized': 'г Москва, ул Ленина, д 1',
                'quality_code': 0,
                'components': {'city': 'Москва'},
            },
        ):
            address = await AddressService.normalize_address(
                'Москва Ленина 1',
            )

        # 3. Создание заказа
        order = OrderService.create_order(
            user_tg_id=111,
            user_name='Иван Иванов',
            user_phone='+79991234567',
            user_address=address['normalized'],
            user_address_raw='Москва Ленина 1',
            cart_items=cart_items,
            promo=None,
            delivery_cost=Decimal('300'),
        )

        assert order.status == 'new'
        # subtotal = 500*2 + 300*1 = 1300
        # total = 1300 + 300 = 1600
        assert order.total == Decimal('1600.00')
        assert OrderItem.objects.filter(order=order).count() == 2

        # 4. Генерация ссылки на оплату (мок YooKassa)
        with patch(
            'payments.services.YooKassaPayment',
        ) as mock_yk:
            mock_yk.create.return_value = MagicMock(
                id='pay_test_123',
                confirmation=MagicMock(
                    confirmation_url='https://pay.example.com',
                ),
            )
            result = PaymentService.create_sbp_invoice(order)

        assert 'confirmation_url' in result
        assert result['payment_id'] == 'pay_test_123'

        # 5. Stock уменьшился
        p1.refresh_from_db()
        p2.refresh_from_db()
        assert p1.stock == 8
        assert p2.stock == 4
