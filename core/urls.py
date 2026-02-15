"""
URL-конфигурация tg-shop-engine.

Эндпоинты:
- /admin/ — Django Admin
- /webhook/telegram — Telegram Bot webhook
- /webhook/yookassa — YooKassa payment callback
"""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Webhook endpoints добавляются в Phase 5 (payments)
    # path('webhook/telegram', ...),
    # path('webhook/yookassa', ...),
]
