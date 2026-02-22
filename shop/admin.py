"""Django Admin — модели интернет-магазина."""

import csv
from datetime import date, timedelta
from decimal import Decimal
import io

from django.contrib import admin
from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from shop.models import (
    Category,
    Order,
    OrderItem,
    Product,
    PromoCode,
)


class OrderItemInline(admin.TabularInline):
    """Позиции заказа (read-only inline)."""

    model = OrderItem
    extra = 0
    readonly_fields = (
        'product',
        'product_name',
        'quantity',
        'price',
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Категории товаров."""

    list_display = ('name', 'sort_order', 'is_active')
    list_filter = ('is_active',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Товары."""

    list_display = (
        'name',
        'category',
        'price',
        'stock',
        'is_active',
    )
    list_filter = ('is_active', 'category')
    search_fields = ('name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Заказы."""

    list_display = (
        'uuid',
        'user_name',
        'status',
        'total',
        'created_at',
    )
    list_filter = ('status', 'created_at')
    inlines = [OrderItemInline]
    actions = ['export_orders_csv']

    @admin.action(
        description='Экспорт выбранных заказов в CSV',
    )
    def export_orders_csv(self, request, queryset):
        """Экспорт заказов в CSV (UTF-8 BOM)."""
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM
        writer = csv.writer(output)
        writer.writerow(
            [
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
        )
        orders = queryset.prefetch_related('items')
        for order in orders:
            items = '; '.join(
                f'{i.product_name} x{i.quantity}' for i in order.items.all()
            )
            writer.writerow(
                [
                    str(order.uuid),
                    order.user_name,
                    order.user_phone,
                    order.user_address,
                    order.status,
                    str(order.subtotal),
                    str(order.discount_amount),
                    str(order.delivery_cost),
                    str(order.total),
                    order.payment_method or '',
                    order.created_at.isoformat(),
                    items,
                ]
            )
        response = HttpResponse(
            output.getvalue().encode('utf-8'),
            content_type='text/csv; charset=utf-8',
        )
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        return response


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    """Промокоды."""

    list_display = (
        'code',
        'discount_type',
        'discount_value',
        'used_count',
        'max_uses',
        'is_active',
    )
    list_filter = ('is_active', 'discount_type')


# === Analytics dashboard ===


@staff_member_required
def analytics_view(request):
    """Панель аналитики: выручка, заказы, средний чек."""
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    today = timezone.now().date()

    if date_from_str:
        date_from = date.fromisoformat(date_from_str)
    else:
        date_from = today - timedelta(days=30)

    date_to = date.fromisoformat(date_to_str) if date_to_str else today

    qs = Order.objects.filter(
        status='paid',
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    stats = qs.aggregate(
        total_revenue=Sum('total'),
        order_count=Count('id'),
    )
    total_revenue = stats['total_revenue'] or Decimal('0')
    order_count = stats['order_count'] or 0

    if order_count:
        avg_order_value = total_revenue / order_count
    else:
        avg_order_value = Decimal('0')

    context = {
        'total_revenue': total_revenue,
        'order_count': order_count,
        'avg_order_value': avg_order_value,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(
        request,
        'admin/analytics.html',
        context,
    )
