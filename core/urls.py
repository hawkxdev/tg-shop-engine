"""
URL-конфигурация tg-shop-engine.

Эндпоинты:
- /admin/ — Django Admin
- /webhook/telegram — Telegram Bot webhook
- /webhook/yookassa — YooKassa payment callback
"""

from django.contrib import admin
from django.urls import path

from payments.views import telegram_webhook, yookassa_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhook/telegram', telegram_webhook),
    path('webhook/yookassa', yookassa_webhook),
]
