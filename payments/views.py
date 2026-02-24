"""Webhook представления."""

import json

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from asgiref.sync import sync_to_async
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import structlog

from bot.setup import create_bot, create_dispatcher
from payments.services import PaymentService

logger = structlog.get_logger(__name__)

# Lazy singletons: init on first request
_bot: Bot | None = None
_dp: Dispatcher | None = None


def _get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = create_bot()
    return _bot


def _get_dp() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = create_dispatcher()
    return _dp


def _get_client_ip(request: HttpRequest) -> str:
    """IP клиента с учётом прокси."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        return str(x_forwarded_for).split(',')[0].strip()
    return str(request.META.get('REMOTE_ADDR', ''))


@csrf_exempt
async def telegram_webhook(request: HttpRequest) -> HttpResponse:
    """Приём Telegram webhook."""
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
    """Приём YooKassa webhook."""
    if request.method != 'POST':
        return HttpResponse(status=405)

    client_ip = _get_client_ip(request)
    try:
        await sync_to_async(PaymentService.handle_yookassa_webhook)(
            body=request.body,
            client_ip=client_ip,
        )
    except PermissionDenied:
        return HttpResponse(status=403)
    except Exception:
        logger.exception('yookassa_webhook_error', client_ip=client_ip)
        return HttpResponse(status=500)

    return HttpResponse(status=200)
