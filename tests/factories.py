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
