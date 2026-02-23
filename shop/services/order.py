"""Сервис создания и управления заказами."""

from decimal import Decimal

from django.db import transaction
from django.db.models import F
import structlog

from bot.services.notification import NotificationService
from shop.models import (
    STATUS_TRANSITIONS,
    Order,
    OrderItem,
    Product,
    PromoCode,
)
from shop.services.promo import PromoService

logger = structlog.get_logger(__name__)


class InsufficientStockError(Exception):
    """Недостаточно товара на складе."""


class InvalidStatusTransitionError(Exception):
    """Недопустимый переход статуса заказа."""


class OrderService:
    """Операции с заказами."""

    @staticmethod
    @transaction.atomic
    def create_order(
        *,
        user_tg_id: int,
        user_name: str,
        user_phone: str,
        user_address: str,
        user_address_raw: str | None = None,
        cart_items: dict[int, int],
        promo: PromoCode | None = None,
        delivery_cost: Decimal = Decimal('0'),
    ) -> Order:
        """Создание заказа из корзины."""
        product_ids = list(cart_items.keys())
        products = Product.objects.select_for_update().filter(
            id__in=product_ids
        )

        products_map = {}
        for product in products:
            qty = cart_items[product.id]
            if product.stock < qty:
                raise InsufficientStockError(
                    f'{product.name}: запрошено {qty}, '
                    f'на складе {product.stock}'
                )
            products_map[product.id] = product

        subtotal = Decimal('0')
        for pid, qty in cart_items.items():
            subtotal += products_map[pid].price * qty

        discount_amount = Decimal('0')
        if promo:
            discount_amount, delivery_cost = PromoService.apply_discount(
                subtotal=subtotal,
                delivery_cost=delivery_cost,
                promo=promo,
            )

        total = subtotal + delivery_cost - discount_amount

        order = Order.objects.create(
            user_tg_id=user_tg_id,
            user_name=user_name,
            user_phone=user_phone,
            user_address=user_address,
            user_address_raw=user_address_raw or '',
            status='new',
            subtotal=subtotal,
            discount_amount=discount_amount,
            delivery_cost=delivery_cost,
            total=total,
            promo_code=promo,
        )

        if promo:
            PromoService.record_usage(
                promo=promo,
                user_tg_id=user_tg_id,
                order=order,
            )

        for pid, qty in cart_items.items():
            product = products_map[pid]
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=qty,
                price=product.price,
            )
            Product.objects.filter(id=pid).update(stock=F('stock') - qty)

        logger.info(
            'order_created',
            order_id=order.id,
            user_tg_id=user_tg_id,
            total=str(total),
            promo=promo.code if promo else None,
        )
        return order

    @staticmethod
    def update_status(order_id: int, new_status: str) -> Order:
        """Обновление статуса заказа."""
        order = Order.objects.get(id=order_id)
        allowed = STATUS_TRANSITIONS.get(order.status, ())
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f'{order.status} → {new_status} недопустим'
            )
        old_status = order.status
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])
        logger.info(
            'order_status_updated',
            order_id=order_id,
            old_status=old_status,
            new_status=new_status,
        )

        # notify_buyer async из sync: MVP trade-off
        NotificationService.notify_buyer(  # type: ignore[unused-coroutine]
            bot=None,
            user_tg_id=order.user_tg_id,
            order=order,
            event='status_changed',
        )

        return order
