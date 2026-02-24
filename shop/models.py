"""Модели интернет-магазина."""

from decimal import Decimal
from typing import Any
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

_TRANSLIT = {
    'а': 'a',
    'б': 'b',
    'в': 'v',
    'г': 'g',
    'д': 'd',
    'е': 'e',
    'ё': 'yo',
    'ж': 'zh',
    'з': 'z',
    'и': 'i',
    'й': 'y',
    'к': 'k',
    'л': 'l',
    'м': 'm',
    'н': 'n',
    'о': 'o',
    'п': 'p',
    'р': 'r',
    'с': 's',
    'т': 't',
    'у': 'u',
    'ф': 'f',
    'х': 'kh',
    'ц': 'ts',
    'ч': 'ch',
    'ш': 'sh',
    'щ': 'shch',
    'ъ': '',
    'ы': 'y',
    'ь': '',
    'э': 'e',
    'ю': 'yu',
    'я': 'ya',
}


def _make_slug(value: str) -> str:
    """Транслитерация и генерация slug."""
    transliterated = ''.join(_TRANSLIT.get(c, c) for c in value.lower())
    return slugify(transliterated)


class Category(models.Model):
    """Категория товаров."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(
                fields=['is_active', 'sort_order'],
                name='cat_active_sort',
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = _make_slug(self.name)
        super().save(*args, **kwargs)


ORDER_STATUS_NEW = 'new'
ORDER_STATUS_PENDING = 'pending_payment'
ORDER_STATUS_PAID = 'paid'
ORDER_STATUS_SHIPPED = 'shipped'
ORDER_STATUS_DELIVERED = 'delivered'
ORDER_STATUS_CANCELLED = 'cancelled'

ORDER_STATUS_CHOICES = [
    (ORDER_STATUS_NEW, 'Новый'),
    (ORDER_STATUS_PENDING, 'Ожидает оплаты'),
    (ORDER_STATUS_PAID, 'Оплачен'),
    (ORDER_STATUS_SHIPPED, 'Отправлен'),
    (ORDER_STATUS_DELIVERED, 'Доставлен'),
    (ORDER_STATUS_CANCELLED, 'Отменён'),
]

PAYMENT_SBP = 'sbp'
PAYMENT_STARS = 'stars'

PAYMENT_METHOD_CHOICES = [
    (PAYMENT_SBP, 'СБП'),
    (PAYMENT_STARS, 'Telegram Stars'),
]

DISCOUNT_PERCENTAGE = 'percentage'
DISCOUNT_FREE_DELIVERY = 'free_delivery'

DISCOUNT_TYPE_CHOICES = [
    (DISCOUNT_PERCENTAGE, 'Процент'),
    (DISCOUNT_FREE_DELIVERY, 'Бесплатная доставка'),
]

STATUS_TRANSITIONS = {
    ORDER_STATUS_NEW: (ORDER_STATUS_PENDING,),
    ORDER_STATUS_PENDING: (ORDER_STATUS_PAID, ORDER_STATUS_CANCELLED),
    ORDER_STATUS_PAID: (ORDER_STATUS_SHIPPED, ORDER_STATUS_CANCELLED),
    ORDER_STATUS_SHIPPED: (ORDER_STATUS_DELIVERED,),
    ORDER_STATUS_DELIVERED: (),
    ORDER_STATUS_CANCELLED: (),
}


class Product(models.Model):
    """Товар."""

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(max_length=500)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    photo = models.ImageField(upload_to='products/')
    stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['is_active', 'category'],
                name='prod_active_cat',
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = _make_slug(self.name)
        super().save(*args, **kwargs)


class Order(models.Model):
    """Заказ покупателя."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user_tg_id = models.BigIntegerField()
    user_name = models.CharField(max_length=200)
    user_phone = models.CharField(max_length=20)
    user_address = models.TextField()
    user_address_raw = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='new',
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
    )
    delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    promo_code = models.ForeignKey(
        'PromoCode',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='orders',
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        default='',
    )
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['user_tg_id', '-created_at'],
                name='order_user_created',
            ),
            models.Index(
                fields=['status'],
                name='order_status',
            ),
            models.Index(
                fields=['-created_at'],
                name='order_created_at',
            ),
        ]

    def __str__(self) -> str:
        return f'Заказ {self.uuid} ({self.get_status_display()})'


class OrderItem(models.Model):
    """Позиция заказа."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
    )
    product_name = models.CharField(max_length=200)
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        ordering = ['id']

    def __str__(self) -> str:
        return f'{self.product_name} x{self.quantity}'


class PromoCode(models.Model):
    """Промокод на скидку."""

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
    )
    discount_value = models.DecimalField(max_digits=5, decimal_places=2)
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
    )
    max_uses = models.IntegerField(blank=True, null=True)
    max_uses_per_user = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.code

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.code = self.code.upper()
        super().save(*args, **kwargs)


class PromoCodeUsage(models.Model):
    """Факт использования промокода."""

    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.CASCADE,
        related_name='usages',
    )
    user_tg_id = models.BigIntegerField()
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='promo_usages',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Использование промокода'
        verbose_name_plural = 'Использования промокодов'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['promo_code', 'order'],
                name='unique_promo_per_order',
            ),
        ]
        indexes = [
            models.Index(
                fields=['promo_code', 'user_tg_id'],
                name='promo_user_lookup',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.promo_code.code} → заказ {self.order_id}'
