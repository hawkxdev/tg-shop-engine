"""Сервис нормализации адреса через DaData Clean API."""

import logging
from typing import Any

from django.conf import settings
import httpx

logger = logging.getLogger(__name__)

_DADATA_CLEAN_URL = 'https://cleaner.dadata.ru/api/v1/clean/address'
_TIMEOUT = 3.0


class AddressService:
    """Нормализация адресов через DaData."""

    @staticmethod
    async def normalize_address(raw_address: str) -> dict[str, Any]:
        """Нормализация адреса через DaData Clean API.

        Args:
            raw_address: Исходная строка адреса.

        Returns:
            dict с ключами: normalized, quality_code, components.
            При ошибке: normalized=raw_address, quality_code=-1.
        """
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT,
            ) as client:
                response = await client.post(
                    _DADATA_CLEAN_URL,
                    json=[raw_address],
                    headers={
                        'Authorization': f'Token {settings.DADATA_API_KEY}',
                        'X-Secret': settings.DADATA_SECRET,
                        'Content-Type': 'application/json',
                    },
                )
                response.raise_for_status()
                data = response.json()

            if not data:
                return _fallback(raw_address)

            item = data[0]
            return {
                'normalized': item.get('result', raw_address),
                'quality_code': item.get('qc', -1),
                'components': {
                    k: v for k, v in item.items() if k not in ('result', 'qc')
                },
            }
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning('DaData недоступен: %s', exc)
            return _fallback(raw_address)


def _fallback(raw_address):
    """Возврат исходного адреса при ошибке."""
    return {
        'normalized': raw_address,
        'quality_code': -1,
        'components': {},
    }
