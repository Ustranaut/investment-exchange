from django.core.validators import MinValueValidator
from django.db import models


class PackageQuote(models.Model):
    package = models.OneToOneField("packages.Package", on_delete=models.CASCADE, related_name="quote")
    current_price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    change_percent = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Текущая котировка"
        verbose_name_plural = "Текущие котировки"

    def __str__(self):
        return f"{self.package.name}: {self.current_price}"


class QuoteHistory(models.Model):
    quote = models.ForeignKey(PackageQuote, on_delete=models.CASCADE, related_name="history")
    price = models.DecimalField(max_digits=14, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("recorded_at",)
        verbose_name = "История котировок"
        verbose_name_plural = "История котировок"
        indexes = [models.Index(fields=("quote", "recorded_at"))]

    def __str__(self):
        return f"{self.quote.package.name}: {self.price}"
