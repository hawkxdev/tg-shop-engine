"""Юнит-тесты AddressService.normalize_address()."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from shop.services.address import AddressService


@pytest.fixture
def dadata_client():
    """Мок httpx.AsyncClient для вызовов DaData."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    with patch(
        'shop.services.address.httpx.AsyncClient',
        return_value=client,
    ):
        yield client


class TestNormalizeAddress:
    """Тесты нормализации адреса через DaData Clean API."""

    @pytest.mark.asyncio
    async def test_success(self, dadata_client):
        """DaData возвращает нормализованный адрес."""
        response = MagicMock()
        response.json.return_value = [
            {
                'result': 'г Москва, ул Ленина, д 1',
                'qc': 0,
                'city': 'Москва',
                'street': 'Ленина',
                'house': '1',
            },
        ]
        response.raise_for_status = MagicMock()
        dadata_client.post.return_value = response

        result = await AddressService.normalize_address(
            'Москва Ленина 1',
        )

        assert result['normalized'] == 'г Москва, ул Ленина, д 1'
        assert result['quality_code'] == 0
        assert 'components' in result

    @pytest.mark.asyncio
    async def test_timeout_fallback(self, dadata_client):
        """При таймауте — исходный адрес, quality_code=-1."""
        dadata_client.post.side_effect = httpx.TimeoutException('Таймаут')

        result = await AddressService.normalize_address(
            'Москва Ленина 1',
        )

        assert result['normalized'] == 'Москва Ленина 1'
        assert result['quality_code'] == -1
        assert result['components'] == {}

    @pytest.mark.asyncio
    async def test_error_fallback(self, dadata_client):
        """При ошибке сети — исходный адрес, quality_code=-1."""
        dadata_client.post.side_effect = httpx.HTTPError(
            'DaData недоступен',
        )

        result = await AddressService.normalize_address(
            'Москва Ленина 1',
        )

        assert result['normalized'] == 'Москва Ленина 1'
        assert result['quality_code'] == -1
        assert result['components'] == {}
