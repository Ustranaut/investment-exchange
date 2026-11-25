from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class Package(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Активный"
        ARCHIVED = "archived", "Архив"

    name = models.CharField("Название", max_length=150)
    slug = models.SlugField("URL", max_length=180, unique=True)
    description = models.TextField("Описание", blank=True)
    price = models.DecimalField(
        "Цена, ₽", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    duration_days = models.PositiveIntegerField(
        "Срок, дней", validators=[MinValueValidator(1)]
    )
    annual_yield_percent = models.DecimalField(
        "Условная годовая доходность, %",
        max_digits=7, decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    total_limit = models.PositiveIntegerField(
        "Общий лимит", null=True, blank=True,
        help_text="Оставьте пустым, если лимит не ограничен.",
    )
    allocated_count = models.PositiveIntegerField("Зарезервировано", default=0)
    status = models.CharField(
        "Статус", max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    image = models.ImageField("Изображение", upload_to="packages/", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Пакет"
        verbose_name_plural = "Пакеты"
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="package_price_nonnegative"),
            models.CheckConstraint(condition=Q(duration_days__gte=1), name="package_duration_positive"),
            models.CheckConstraint(condition=Q(annual_yield_percent__gte=0), name="package_yield_nonnegative"),
            models.CheckConstraint(
                condition=Q(total_limit__isnull=True) | Q(allocated_count__lte=F("total_limit")),
                name="package_allocated_within_limit",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_unlimited(self):
        return self.total_limit is None

    @property
    def available_count(self):
        if self.is_unlimited:
            return None
        return self.total_limit - self.allocated_count
