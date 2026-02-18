"""Конфигурация pytest — базовые фикстуры для всех тестов."""

from unittest.mock import AsyncMock

from django.test import AsyncClient
import pytest


@pytest.fixture
def async_client() -> AsyncClient:
    """Асинхронный тест-клиент Django."""
    return AsyncClient()


@pytest.fixture
def bot_mock() -> AsyncMock:
    """Мок aiogram Bot без реального API."""
    mock = AsyncMock()
    mock.id = 123456789
    mock.username = 'test_shop_bot'
    return mock


@pytest.fixture
def redis_mock() -> AsyncMock:
    """Мок Redis-клиента для тестирования FSM storage."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.expire = AsyncMock(return_value=True)
    return mock
