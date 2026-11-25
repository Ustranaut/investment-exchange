from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "package_name_snapshot", "unit_price_snapshot",
        "duration_days_snapshot", "annual_yield_percent_snapshot",
        "quantity", "discount_amount_snapshot", "net_amount_snapshot",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "total_amount", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "user__email")
    readonly_fields = ("order_number", "subtotal", "discount_amount", "total_amount", "created_at", "updated_at")
    inlines = (OrderItemInline,)
