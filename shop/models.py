"""Модели интернет-магазина."""

from decimal import Decimal
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


def _make_slug(value):
    """Транслитерация кириллицы и генерация slug."""
    result = []
    for char in value.lower():
        result.append(_TRANSLIT.get(char, char))
    return slugify(''.join(result))


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

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _make_slug(self.name)
        super().save(*args, **kwargs)


# --- Статусы заказа ---

ORDER_STATUS_CHOICES = [
    ('new', 'Новый'),
    ('pending_payment', 'Ожидает оплаты'),
    ('paid', 'Оплачен'),
    ('shipped', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('cancelled', 'Отменён'),
]

PAYMENT_METHOD_CHOICES = [
    ('sbp', 'СБП'),
    ('stars', 'Telegram Stars'),
]

STATUS_TRANSITIONS = {
    'new': ('pending_payment',),
    'pending_payment': ('paid', 'cancelled'),
    'paid': ('shipped', 'cancelled'),
    'shipped': ('delivered',),
    'delivered': (),
    'cancelled': (),
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

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
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
    user_address_raw = models.TextField(blank=True, null=True)
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
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True,
    )
    note = models.TextField(blank=True, null=True)
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
        ]

    def __str__(self):
        return f'Заказ {self.uuid} ({self.get_status_display()})'


class OrderItem(models.Model):
    """Позиция заказа (снимок товара на момент покупки)."""

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

    def __str__(self):
        return f'{self.product_name} x{self.quantity}'
