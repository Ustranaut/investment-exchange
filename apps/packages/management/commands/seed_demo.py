from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.packages.models import Package
from apps.market.models import PackageQuote, QuoteHistory


class Command(BaseCommand):
    help = "Создаёт демонстрационные пакеты и стартовые котировки."

    def handle(self, *args, **options):
        demo = [
            {
                "name": "Стартовый пакет",
                "slug": "starter",
                "description": "Демонстрационный пакет для знакомства с симулятором.",
                "price": Decimal("5000.00"),
                "duration_days": 30,
                "annual_yield_percent": Decimal("12.0000"),
                "total_limit": 100,
            },
            {
                "name": "Стандартный пакет",
                "slug": "standard",
                "description": "Учебный пакет со средним сроком моделирования.",
                "price": Decimal("15000.00"),
                "duration_days": 90,
                "annual_yield_percent": Decimal("18.0000"),
                "total_limit": 50,
            },
            {
                "name": "Премиум пакет",
                "slug": "premium",
                "description": "Демонстрационный пакет с увеличенным сроком.",
                "price": Decimal("50000.00"),
                "duration_days": 180,
                "annual_yield_percent": Decimal("24.0000"),
                "total_limit": 20,
            },
        ]

        for data in demo:
            package, created = Package.objects.update_or_create(
                slug=data["slug"],
                defaults={**data, "status": Package.Status.ACTIVE},
            )
            quote, quote_created = PackageQuote.objects.get_or_create(
                package=package,
                defaults={"current_price": package.price, "change_percent": Decimal("0.0000")},
            )
            if quote_created or not quote.history.exists():
                QuoteHistory.objects.create(quote=quote, price=quote.current_price)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Создан' if created else 'Обновлён'} пакет: {package.name}"
                )
            )
        self.stdout.write(self.style.SUCCESS("Демонстрационные данные готовы."))
