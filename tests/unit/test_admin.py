"""Тесты Django Admin: CSV export и analytics dashboard.

T065: unit tests CSV export action.
T066: unit tests analytics view.
"""

import csv
from datetime import timedelta
from decimal import Decimal
import io

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.utils import timezone
import pytest

from shop.admin import OrderAdmin
from shop.models import Order
from tests.factories import OrderFactory, OrderItemFactory

# === T065: CSV export action ===


@pytest.mark.django_db
class TestCSVExportAction:
    """Тесты admin action «Export selected orders to CSV»."""

    def _export(self, orders):
        """Вызывает export_orders_csv → HttpResponse."""
        model_admin = OrderAdmin(Order, AdminSite())
        request = RequestFactory().get('/')
        request.user = User(
            is_staff=True,
            is_superuser=True,
        )
        qs = Order.objects.filter(
            pk__in=[o.pk for o in orders],
        )
        return model_admin.export_orders_csv(
            request,
            qs,
        )

    def test_csv_has_correct_columns(self):
        """Заголовок CSV содержит 12 колонок по контракту."""
        order = OrderFactory(status='paid')
        OrderItemFactory(order=order)
        response = self._export([order])
        raw = response.content.lstrip(
            b'\xef\xbb\xbf',
        ).decode('utf-8')
        reader = csv.reader(io.StringIO(raw))
        header = next(reader)
        expected = [
            'order_uuid',
            'user_name',
            'user_phone',
            'user_address',
            'status',
            'subtotal',
            'discount_amount',
            'delivery_cost',
            'total',
            'payment_method',
            'created_at',
            'items',
        ]
        assert header == expected

    def test_csv_starts_with_utf8_bom(self):
        """CSV начинается с UTF-8 BOM для Excel."""
        order = OrderFactory()
        OrderItemFactory(order=order)
        response = self._export([order])
        assert response.content[:3] == b'\xef\xbb\xbf'

    def test_csv_items_semicolon_separated(self):
        """Позиции заказа разделены точкой с запятой."""
        order = OrderFactory()
        OrderItemFactory(
            order=order,
            product_name='Товар А',
            quantity=2,
        )
        OrderItemFactory(
            order=order,
            product_name='Товар Б',
            quantity=1,
        )
        response = self._export([order])
        raw = response.content.lstrip(
            b'\xef\xbb\xbf',
        ).decode('utf-8')
        reader = csv.reader(io.StringIO(raw))
        next(reader)  # skip header
        row = next(reader)
        items_col = row[-1]  # items — последняя колонка
        assert ';' in items_col


# === T066: Analytics dashboard view ===


@pytest.mark.django_db
class TestAnalyticsView:
    """Тесты analytics dashboard (/admin/analytics/)."""

    def test_total_revenue(self, admin_client):
        """Выручка = сумма total оплаченных заказов."""
        OrderFactory(
            status='paid',
            total=Decimal('1500.00'),
        )
        OrderFactory(
            status='paid',
            total=Decimal('500.00'),
        )
        OrderFactory(
            status='pending_payment',
            total=Decimal('200.00'),
        )
        response = admin_client.get('/admin/analytics/')
        assert response.status_code == 200
        assert response.context['total_revenue'] == Decimal(
            '2000.00',
        )

    def test_order_count(self, admin_client):
        """Количество = только оплаченные заказы."""
        OrderFactory(status='paid')
        OrderFactory(status='paid')
        OrderFactory(status='cancelled')
        response = admin_client.get('/admin/analytics/')
        assert response.context['order_count'] == 2

    def test_average_value(self, admin_client):
        """Средний чек = выручка / количество."""
        OrderFactory(
            status='paid',
            total=Decimal('1000.00'),
        )
        OrderFactory(
            status='paid',
            total=Decimal('2000.00'),
        )
        response = admin_client.get('/admin/analytics/')
        assert response.context['avg_order_value'] == Decimal(
            '1500.00',
        )

    def test_date_range_filtering(self, admin_client):
        """Фильтрация по диапазону дат."""
        old = OrderFactory(
            status='paid',
            total=Decimal('1000.00'),
        )
        Order.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=60),
        )
        OrderFactory(
            status='paid',
            total=Decimal('500.00'),
        )
        date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_to = timezone.now().strftime('%Y-%m-%d')
        response = admin_client.get(
            '/admin/analytics/',
            {'date_from': date_from, 'date_to': date_to},
        )
        assert response.context['total_revenue'] == Decimal(
            '500.00',
        )
