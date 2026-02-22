"""Сервис уведомлений покупателей и администратора."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from aiogram import Bot

    from shop.models import Order

logger = structlog.get_logger(__name__)

_BUYER_TEMPLATES = {
    'order_confirmed': ('Ваш заказ {uuid} подтверждён.\nСумма: {total} ₽'),
    'payment_success': (
        'Оплата заказа {uuid} прошла успешно!\nОжидайте отправки.'
    ),
    'status_changed': ('Статус заказа {uuid} изменён: {status}'),
}

_ADMIN_TEMPLATES = {
    'new_paid_order': (
        'Новый оплаченный заказ {uuid}\n'
        'Покупатель: {user_name}\n'
        'Телефон: {user_phone}\n'
        'Сумма: {total} ₽'
    ),
}


class NotificationService:
    """Отправка уведомлений в Telegram."""

    @staticmethod
    async def notify_buyer(
        bot: Bot | None, user_tg_id: int, order: Order, event: str
    ) -> None:
        """Уведомление покупателя о событии заказа.

        Args:
            bot: Экземпляр aiogram.Bot.
            user_tg_id: Telegram ID покупателя.
            order: Order.
            event: Тип события (order_confirmed,
                   payment_success, status_changed).
        """
        template = _BUYER_TEMPLATES.get(event)
        if not template:
            logger.warning('unknown_buyer_event', event=event)
            return

        text = template.format(
            uuid=order.uuid,
            total=order.total,
            status=order.get_status_display(),
        )

        try:
            await bot.send_message(user_tg_id, text)
        except Exception:
            logger.exception(
                'buyer_notification_failed', user_tg_id=user_tg_id
            )

    @staticmethod
    async def notify_admin(
        bot: Bot, chat_id: int, order: Order, event: str
    ) -> None:
        """Уведомление администратора о событии заказа.

        Args:
            bot: Экземпляр aiogram.Bot.
            chat_id: ID чата администратора.
            order: Order.
            event: Тип события (new_paid_order).
        """
        template = _ADMIN_TEMPLATES.get(event)
        if not template:
            logger.warning('unknown_admin_event', event=event)
            return

        text = template.format(
            uuid=order.uuid,
            user_name=order.user_name,
            user_phone=order.user_phone,
            total=order.total,
        )

        try:
            await bot.send_message(chat_id, text)
        except Exception:
            logger.exception('admin_notification_failed', chat_id=chat_id)
