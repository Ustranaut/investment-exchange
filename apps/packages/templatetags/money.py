from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def money(value):
    try:
        amount = Decimal(str(value))
        formatted = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
        return f"{formatted} ₽"
    except (InvalidOperation, TypeError, ValueError):
        return value
