from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Promotion(models.Model):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Процент"
        FIXED = "fixed", "Фиксированная сумма"

    name = models.CharField("Название акции", max_length=150)
    description = models.TextField("Описание", blank=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    min_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    packages = models.ManyToManyField("packages.Package", through="PromotionPackage", blank=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self):
        return self.name

    @property
    def is_current(self):
        now = timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at


class PromoCode(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="promo_codes")
    code = models.CharField(max_length=40, unique=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class PromotionPackage(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    package = models.ForeignKey("packages.Package", on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("promotion", "package"), name="unique_promotion_package")
        ]


class PromotionRedemption(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="promotion_redemption")
    promo_code = models.ForeignKey(PromoCode, on_delete=models.PROTECT, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Применение акции"
        verbose_name_plural = "Применения акций"
