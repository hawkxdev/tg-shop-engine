"""Django Admin платежей."""

from django.contrib import admin
from django.http import HttpRequest

from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Платежи (только просмотр)."""

    list_display = (
        'order',
        'provider',
        'status',
        'amount',
        'created_at',
    )
    list_filter = ('provider', 'status')
    search_fields = ('provider_payment_id', 'idempotency_key')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Payment | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: Payment | None = None
    ) -> bool:
        return False
