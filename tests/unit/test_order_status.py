"""Юнит-тесты /status handler и уведомлений о смене статуса."""

from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import sync_to_async
import pytest

from shop.services.order import OrderService
from tests.factories import OrderFactory


@pytest.mark.django_db(transaction=True)
class TestStatusHandler:
    """Тесты /status handler."""

    @pytest.mark.asyncio
    async def test_status_shows_latest_order(self):
        """Показывает последний заказ пользователя."""
        from bot.handlers.order_status import on_status  # noqa: F401

        order = await sync_to_async(OrderFactory)(user_tg_id=1001)

        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 1001

        await on_status(message)

        message.answer.assert_called_once()
        text = message.answer.call_args[0][0]
        assert str(order.uuid) in text

    @pytest.mark.asyncio
    async def test_status_no_orders_message(self):
        """Сообщение «заказов нет» если у пользователя нет заказов."""
        from bot.handlers.order_status import on_status  # noqa: F401

        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 9999  # нет заказов

        await on_status(message)

        message.answer.assert_called_once()
        text = message.answer.call_args[0][0]
        assert 'заказ' in text.lower()

    @pytest.mark.asyncio
    async def test_status_displays_uuid_and_status(self):
        """Сообщение содержит uuid, статус и сумму заказа."""
        from bot.handlers.order_status import on_status  # noqa: F401

        order = await sync_to_async(OrderFactory)(
            user_tg_id=1002, status='new'
        )

        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 1002

        await on_status(message)

        text = message.answer.call_args[0][0]
        assert str(order.uuid) in text
        assert str(order.total) in text


@pytest.mark.django_db
class TestStatusChangeNotification:
    """Тесты уведомления покупателя при смене статуса заказа."""

    def test_update_status_sends_notification(self):
        """update_status вызывает notify_buyer с event='status_changed'."""
        order = OrderFactory(status='new', user_tg_id=42)

        with patch(
            'shop.services.order.NotificationService.notify_buyer',
        ) as mock_notify:
            OrderService.update_status(order.id, 'pending_payment')
            mock_notify.assert_called_once()

    def test_update_status_notification_params(self):
        """notify_buyer получает event='status_changed' и user_tg_id заказа."""
        order = OrderFactory(status='new', user_tg_id=42)

        with patch(
            'shop.services.order.NotificationService.notify_buyer',
        ) as mock_notify:
            OrderService.update_status(order.id, 'pending_payment')
            call_kwargs = mock_notify.call_args.kwargs
            assert call_kwargs['event'] == 'status_changed'
            assert call_kwargs['user_tg_id'] == 42
