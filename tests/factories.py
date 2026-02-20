"""Фабрики Factory Boy для тестирования моделей."""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory, ImageField


class CategoryFactory(DjangoModelFactory):
    """Фабрика категорий."""

    class Meta:
        model = 'shop.Category'

    name = factory.Sequence(lambda n: f'Категория {n}')
    slug = factory.Sequence(lambda n: f'category-{n}')
    sort_order = factory.Sequence(lambda n: n)
    is_active = True


class ProductFactory(DjangoModelFactory):
    """Фабрика товаров."""

    class Meta:
        model = 'shop.Product'

    category = factory.SubFactory(CategoryFactory)
    name = factory.Sequence(lambda n: f'Товар {n}')
    slug = factory.Sequence(lambda n: f'product-{n}')
    description = factory.Faker('sentence', nb_words=10)
    price = factory.LazyFunction(lambda: Decimal('99.99'))
    photo = ImageField(filename='test_product.jpg')
    stock = 10
    is_active = True


class OrderFactory(DjangoModelFactory):
    """Фабрика заказов."""

    class Meta:
        model = 'shop.Order'

    user_tg_id = factory.Sequence(lambda n: 100_000 + n)
    user_name = factory.Faker('name', locale='ru_RU')
    user_phone = factory.Sequence(lambda n: f'+7999{n:07d}')
    user_address = factory.Faker('address', locale='ru_RU')
    status = 'new'
    subtotal = factory.LazyFunction(lambda: Decimal('500.00'))
    delivery_cost = factory.LazyFunction(lambda: Decimal('300.00'))
    total = factory.LazyFunction(lambda: Decimal('800.00'))


class OrderItemFactory(DjangoModelFactory):
    """Фабрика позиций заказа."""

    class Meta:
        model = 'shop.OrderItem'

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    product_name = factory.LazyAttribute(lambda o: o.product.name)
    quantity = 1
    price = factory.LazyAttribute(lambda o: o.product.price)


class PromoCodeFactory(DjangoModelFactory):
    """Фабрика промокодов."""

    class Meta:
        model = 'shop.PromoCode'

    code = factory.Sequence(lambda n: f'PROMO{n:04d}')
    discount_type = 'percentage'
    discount_value = factory.LazyFunction(lambda: Decimal('10.00'))
    min_order_amount = factory.LazyFunction(lambda: Decimal('0'))
    max_uses = None
    max_uses_per_user = 1
    is_active = True


class PromoCodeUsageFactory(DjangoModelFactory):
    """Фабрика использований промокодов."""

    class Meta:
        model = 'shop.PromoCodeUsage'

    promo_code = factory.SubFactory(PromoCodeFactory)
    user_tg_id = factory.Sequence(lambda n: 100_000 + n)
    order = factory.SubFactory(OrderFactory)


class PaymentFactory(DjangoModelFactory):
    """Фабрика платежей."""

    class Meta:
        model = 'payments.Payment'

    order = factory.SubFactory(OrderFactory)
    provider = 'yookassa'
    amount = factory.LazyAttribute(lambda o: o.order.total)
    currency = 'RUB'
    status = 'pending'
