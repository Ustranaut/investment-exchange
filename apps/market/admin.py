from django.contrib import admin
from .models import PackageQuote, QuoteHistory


class QuoteHistoryInline(admin.TabularInline):
    model = QuoteHistory
    extra = 0
    readonly_fields = ("price", "recorded_at")
    can_delete = False


@admin.register(PackageQuote)
class PackageQuoteAdmin(admin.ModelAdmin):
    list_display = ("package", "current_price", "change_percent", "updated_at")
    inlines = (QuoteHistoryInline,)


@admin.register(QuoteHistory)
class QuoteHistoryAdmin(admin.ModelAdmin):
    list_display = ("quote", "price", "recorded_at")
    readonly_fields = ("quote", "price", "recorded_at")
