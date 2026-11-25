from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.packages.models import Package
from .models import Order, OrderItem


@transaction.atomic
def create_order(*, user, items):
    """
    Создаёт заказ и резервирует лимит пакетов.
    items: список словарей вида {"package_id": 1, "quantity": 2}.
    """
    quantities = {}
    for item in items:
        package_id = int(item["package_id"])
        quantity = int(item.get("quantity", 1))
        if quantity < 1:
            raise ValidationError("Количество должно быть не меньше 1.")
        quantities[package_id] = quantities.get(package_id, 0) + quantity

    if not quantities:
        raise ValidationError("Заказ не может быть пустым.")

    package_ids = sorted(quantities)
    packages = list(
        Package.objects.select_for_update().filter(id__in=package_ids).order_by("id")
    )
    if len(packages) != len(package_ids):
        raise ValidationError("Один из пакетов не найден.")

    subtotal = Decimal("0.00")
    order = Order.objects.create(user=user)

    for package in packages:
        quantity = quantities[package.id]
        if package.status != Package.Status.ACTIVE:
            raise ValidationError(f"Пакет «{package.name}» недоступен.")
        if package.total_limit is not None and package.allocated_count + quantity > package.total_limit:
            raise ValidationError(f"Недостаточно свободных единиц пакета «{package.name}».")

        package.allocated_count += quantity
        package.save(update_fields=("allocated_count",))

        line_total = package.price * quantity
        subtotal += line_total
        OrderItem.objects.create(
            order=order,
            package=package,
            package_name_snapshot=package.name,
            unit_price_snapshot=package.price,
            duration_days_snapshot=package.duration_days,
            annual_yield_percent_snapshot=package.annual_yield_percent,
            quantity=quantity,
            discount_amount_snapshot=Decimal("0.00"),
            net_amount_snapshot=line_total,
        )

    order.subtotal = subtotal
    order.total_amount = subtotal
    order.save(update_fields=("subtotal", "total_amount", "updated_at"))
    return order


@transaction.atomic
def cancel_order(*, order_id):
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == Order.Status.CANCELLED:
        return order
    if order.status == Order.Status.COMPLETED:
        raise ValidationError("Завершённый заказ нельзя отменить.")

    items = list(order.items.all().order_by("package_id"))
    package_ids = sorted({item.package_id for item in items})
    packages = {
        package.id: package
        for package in Package.objects.select_for_update().filter(id__in=package_ids).order_by("id")
    }

    for item in items:
        package = packages[item.package_id]
        package.allocated_count = max(0, package.allocated_count - item.quantity)
        package.save(update_fields=("allocated_count",))

    order.status = Order.Status.CANCELLED
    order.save(update_fields=("status", "updated_at"))
    return order
