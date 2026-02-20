"""Django-представления для вебхуков Telegram и YooKassa."""

import json
import logging

from aiogram.types import Update
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from bot.setup import create_bot, create_dispatcher
from payments.services import PaymentService

logger = logging.getLogger(__name__)

# Ленивые синглтоны: инициализируются при первом запросе.
# Работают корректно в ASGI-режиме (один event loop).
_bot = None
_dp = None


def _get_bot():
    global _bot
    if _bot is None:
        _bot = create_bot()
    return _bot


def _get_dp():
    global _dp
    if _dp is None:
        _dp = create_dispatcher()
    return _dp


def _get_client_ip(request: HttpRequest) -> str:
    """Получить IP-адрес клиента с учётом прокси."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@csrf_exempt
async def telegram_webhook(request: HttpRequest) -> HttpResponse:
    """POST /webhook/telegram — принять обновление от Telegram.

    Передаёт Update в aiogram Dispatcher для обработки.
    Всегда возвращает 200 OK.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        raw = json.loads(request.body)
        update = Update.model_validate(raw)
        await _get_dp().feed_update(_get_bot(), update)
    except Exception:
        logger.exception('Ошибка обработки Telegram webhook')

    return HttpResponse(status=200)


@csrf_exempt
async def yookassa_webhook(request: HttpRequest) -> HttpResponse:
    """POST /webhook/yookassa — принять колбэк от YooKassa.

    Верифицирует IP, передаёт тело в PaymentService.
    Всегда возвращает 200 OK (иначе YooKassa будет повторять запросы).
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    client_ip = _get_client_ip(request)
    try:
        PaymentService.handle_yookassa_webhook(
            body=request.body,
            client_ip=client_ip,
        )
    except Exception:
        logger.exception(
            'Ошибка обработки YooKassa webhook, IP: %s', client_ip
        )

    return HttpResponse(status=200)
