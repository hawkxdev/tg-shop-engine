"""Юнит-тесты OrderService.create_order()."""

from decimal import Decimal

import pytest

from shop.services.order import InsufficientStockError, OrderService
from tests.factories import ProductFactory


@pytest.mark.django_db
class TestCreateOrder:
    """Тесты OrderService.create_order()."""

    def _call(self, cart_items, **kwargs):
        """Вызов create_order с дефолтными параметрами."""
        defaults = {
            'user_tg_id': 111,
            'user_name': 'Иван Иванов',
            'user_phone': '+79991234567',
            'user_address': 'г. Москва, ул. Ленина, 1',
            'user_address_raw': None,
            'cart_items': cart_items,
            'promo': None,
            'delivery_cost': Decimal('300'),
        }
        defaults.update(kwargs)
        return OrderService.create_order(**defaults)

    def test_decrements_stock(self):
        """stock уменьшается атомарно на заказанное количество."""
        product = ProductFactory(stock=10)

        self._call({product.id: 3})

        product.refresh_from_db()
        assert product.stock == 7

    def test_insufficient_stock_raises(self):
        """InsufficientStockError при qty > stock."""
        product = ProductFactory(stock=2)

        with pytest.raises(InsufficientStockError):
            self._call({product.id: 5})

    def test_creates_order_items(self):
        """OrderItem создаётся с ценой-снимком товара."""
        product = ProductFactory(
            price=Decimal('150.00'),
            stock=5,
        )

        order = self._call({product.id: 2})

        items = order.items.all()
        assert items.count() == 1
        item = items.first()
        assert item.quantity == 2
        assert item.price == Decimal('150.00')
        assert item.product_name == product.name

    def test_calculates_total(self):
        """total = subtotal + delivery_cost - discount_amount."""
        p1 = ProductFactory(price=Decimal('100.00'), stock=10)
        p2 = ProductFactory(price=Decimal('200.00'), stock=10)

        order = self._call({p1.id: 2, p2.id: 1})

        # subtotal = 100*2 + 200*1 = 400
        # total = 400 + 300 - 0 = 700
        assert order.subtotal == Decimal('400.00')
        assert order.total == Decimal('700.00')
