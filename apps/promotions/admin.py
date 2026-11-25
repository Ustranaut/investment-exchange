from django.contrib import admin
from .models import Promotion, PromoCode, PromotionPackage, PromotionRedemption


class PromoCodeInline(admin.TabularInline):
    model = PromoCode
    extra = 1


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("name", "discount_type", "discount_value", "starts_at", "ends_at", "is_active")
    list_filter = ("is_active", "discount_type")
    search_fields = ("name",)
    inlines = (PromoCodeInline,)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "promotion", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "promotion__name")


@admin.register(PromotionPackage)
class PromotionPackageAdmin(admin.ModelAdmin):
    list_display = ("promotion", "package")


@admin.register(PromotionRedemption)
class PromotionRedemptionAdmin(admin.ModelAdmin):
    list_display = ("promotion", "user", "order", "discount_amount", "redeemed_at")
    readonly_fields = ("redeemed_at",)
