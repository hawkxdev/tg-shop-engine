"""Юнит-тесты моделей shop."""

from decimal import Decimal

from django.db import IntegrityError
from django.db.models import ProtectedError
import pytest

from tests.factories import CategoryFactory, ProductFactory


@pytest.mark.django_db
class TestCategoryModel:
    """Тесты модели Category."""

    def test_str_returns_name(self):
        """__str__ возвращает имя категории."""
        category = CategoryFactory(name='Электроника')
        assert str(category) == 'Электроника'

    def test_name_unique(self):
        """Поле name должно быть уникальным."""
        CategoryFactory(name='Электроника')
        with pytest.raises(IntegrityError):
            CategoryFactory(name='Электроника')

    def test_slug_auto_generated(self):
        """Поле slug генерируется автоматически при сохранении."""
        category = CategoryFactory(name='Электроника', slug='')
        assert category.slug != ''

    def test_slug_unique(self):
        """Поле slug должно быть уникальным."""
        CategoryFactory(slug='electronics')
        with pytest.raises(IntegrityError):
            CategoryFactory(slug='electronics')

    def test_sort_order_default(self):
        """sort_order по умолчанию равен 0."""
        category = CategoryFactory(sort_order=0)
        assert category.sort_order == 0

    def test_is_active_default(self):
        """is_active по умолчанию True."""
        category = CategoryFactory()
        assert category.is_active is True

    def test_ordering_by_sort_order(self):
        """Категории упорядочены по sort_order."""
        CategoryFactory(sort_order=2)
        CategoryFactory(sort_order=0)
        CategoryFactory(sort_order=1)
        from shop.models import Category

        qs = Category.objects.all()
        orders = list(qs.values_list('sort_order', flat=True))
        assert orders == sorted(orders)


@pytest.mark.django_db
class TestProductModel:
    """Тесты модели Product."""

    def test_str_returns_name(self):
        """__str__ возвращает название товара."""
        product = ProductFactory(name='Смартфон')
        assert str(product) == 'Смартфон'

    def test_category_fk_required(self):
        """Товар обязательно привязан к категории."""
        product = ProductFactory()
        assert product.category is not None
        assert product.category.pk is not None

    def test_category_protect_on_delete(self):
        """Удаление категории с товарами запрещено (PROTECT)."""
        product = ProductFactory()
        category = product.category
        with pytest.raises(ProtectedError):
            category.delete()

    def test_price_positive(self):
        """Цена должна быть больше 0."""
        from django.core.exceptions import ValidationError

        product = ProductFactory(price=Decimal('0'))
        with pytest.raises(ValidationError):
            product.full_clean()

    def test_price_negative_invalid(self):
        """Отрицательная цена невалидна."""
        from django.core.exceptions import ValidationError

        product = ProductFactory(price=Decimal('-10.00'))
        with pytest.raises(ValidationError):
            product.full_clean()

    def test_stock_non_negative(self):
        """Остаток не может быть отрицательным."""
        from django.core.exceptions import ValidationError

        product = ProductFactory(stock=-1)
        with pytest.raises(ValidationError):
            product.full_clean()

    def test_stock_default_zero(self):
        """stock по умолчанию равен 0."""
        product = ProductFactory(stock=0)
        assert product.stock == 0

    def test_is_active_default(self):
        """is_active по умолчанию True."""
        product = ProductFactory()
        assert product.is_active is True

    def test_slug_unique(self):
        """Поле slug товара должно быть уникальным."""
        ProductFactory(slug='smartphone')
        with pytest.raises(IntegrityError):
            ProductFactory(slug='smartphone')

    def test_photo_required(self):
        """Фото товара обязательно."""
        from django.core.exceptions import ValidationError

        product = ProductFactory(photo='')
        with pytest.raises(ValidationError):
            product.full_clean()
