"""Django Admin — модели платежей (read-only)."""

from django.contrib import admin

from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Платежи (read-only)."""

    list_display = (
        'order',
        'provider',
        'status',
        'amount',
        'created_at',
    )
    list_filter = ('provider', 'status')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
