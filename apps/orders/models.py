import uuid
from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        PROCESSING = "processing", "Обрабатывается"
        COMPLETED = "completed", "Завершён"
        CANCELLED = "cancelled", "Отменён"

    order_number = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "created_at")),
            models.Index(fields=("user", "created_at")),
        ]

    def __str__(self):
        return str(self.order_number)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    package = models.ForeignKey("packages.Package", on_delete=models.PROTECT, related_name="order_items")
    package_name_snapshot = models.CharField(max_length=150)
    unit_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days_snapshot = models.PositiveIntegerField()
    annual_yield_percent_snapshot = models.DecimalField(max_digits=7, decimal_places=4)
    quantity = models.PositiveIntegerField(default=1)
    discount_amount_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount_snapshot = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.package_name_snapshot
