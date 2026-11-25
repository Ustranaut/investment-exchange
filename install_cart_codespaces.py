from pathlib import Path

ROOT = Path.cwd()
required = [
    ROOT / 'manage.py',
    ROOT / 'apps/packages/models.py',
    ROOT / 'apps/orders/models.py',
    ROOT / 'config/urls.py',
    ROOT / 'templates/base.html',
]
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    raise SystemExit('Не найдены файлы проекта: ' + ', '.join(missing) + '. Запусти скрипт из корня проекта рядом с manage.py.')

files = {
'apps/orders/cart.py': r'''from decimal import Decimal

from apps.packages.models import Package

CART_SESSION_KEY = "investment_cart"


def get_cart(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(cart, dict):
        cart = {}
    cleaned = {}
    for package_id, quantity in cart.items():
        try:
            package_id = str(int(package_id))
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        if quantity > 0:
            cleaned[package_id] = quantity
    return cleaned


def save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def build_cart(request):
    cart = get_cart(request)
    if not cart:
        return [], Decimal("0.00")

    packages = Package.objects.filter(
        pk__in=[int(package_id) for package_id in cart],
        status=Package.Status.ACTIVE,
    )
    package_map = {str(package.pk): package for package in packages}

    # Remove packages that were deleted or archived after being added.
    stale_ids = set(cart) - set(package_map)
    if stale_ids:
        for package_id in stale_ids:
            cart.pop(package_id, None)
        save_cart(request, cart)

    items = []
    total = Decimal("0.00")
    for package_id, quantity in cart.items():
        package = package_map[package_id]
        line_total = package.price * quantity
        items.append({
            "package": package,
            "quantity": quantity,
            "line_total": line_total,
            "available_count": package.available_count,
            "is_unlimited": package.is_unlimited,
            "is_over_limit": (
                not package.is_unlimited and quantity > package.available_count
            ),
        })
        total += line_total

    return items, total
''',
'apps/orders/views.py': r'''from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.packages.models import Package
from .cart import CART_SESSION_KEY, build_cart, get_cart, save_cart
from .models import Order, OrderItem


def _safe_quantity(value, default=1):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return default
    return quantity


def cart_detail(request):
    items, total = build_cart(request)
    return render(request, "cart/detail.html", {
        "items": items,
        "total": total,
        "has_over_limit": any(item["is_over_limit"] for item in items),
    })


@require_POST
def cart_add(request, package_id):
    package = get_object_or_404(
        Package,
        pk=package_id,
        status=Package.Status.ACTIVE,
    )
    cart = get_cart(request)
    current_quantity = cart.get(str(package.pk), 0)
    add_quantity = _safe_quantity(request.POST.get("quantity"), 1)

    if add_quantity < 1:
        messages.error(request, "Количество должно быть не меньше одного.")
        return redirect("package_detail", slug=package.slug)

    new_quantity = current_quantity + add_quantity
    if not package.is_unlimited and new_quantity > package.available_count:
        messages.error(
            request,
            f"Недостаточно доступных пакетов. Сейчас доступно: {package.available_count}.",
        )
        return redirect("package_detail", slug=package.slug)

    cart[str(package.pk)] = new_quantity
    save_cart(request, cart)
    messages.success(request, f"«{package.name}» добавлен в корзину.")
    return redirect("cart_detail")


@require_POST
def cart_update(request, package_id):
    cart = get_cart(request)
    package_key = str(package_id)
    if package_key not in cart:
        messages.warning(request, "Этого пакета уже нет в корзине.")
        return redirect("cart_detail")

    quantity = _safe_quantity(request.POST.get("quantity"), 0)
    if quantity <= 0:
        cart.pop(package_key, None)
        save_cart(request, cart)
        messages.info(request, "Позиция удалена из корзины.")
        return redirect("cart_detail")

    package = get_object_or_404(
        Package,
        pk=package_id,
        status=Package.Status.ACTIVE,
    )
    if not package.is_unlimited and quantity > package.available_count:
        messages.error(
            request,
            f"Нельзя указать больше доступного количества: {package.available_count}.",
        )
        return redirect("cart_detail")

    cart[package_key] = quantity
    save_cart(request, cart)
    messages.success(request, "Корзина обновлена.")
    return redirect("cart_detail")


@require_POST
def cart_remove(request, package_id):
    cart = get_cart(request)
    cart.pop(str(package_id), None)
    save_cart(request, cart)
    messages.info(request, "Пакет удалён из корзины.")
    return redirect("cart_detail")


@require_POST
def cart_clear(request):
    save_cart(request, {})
    messages.info(request, "Корзина очищена.")
    return redirect("cart_detail")


@login_required
@require_POST
def checkout(request):
    cart = get_cart(request)
    if not cart:
        messages.warning(request, "Корзина пуста.")
        return redirect("cart_detail")

    quantities = {int(package_id): quantity for package_id, quantity in cart.items()}

    with transaction.atomic():
        packages = list(
            Package.objects.select_for_update()
            .filter(pk__in=quantities.keys())
            .order_by("pk")
        )
        package_map = {package.pk: package for package in packages}

        missing_ids = set(quantities) - set(package_map)
        unavailable = [
            package_id for package_id, package in package_map.items()
            if package.status != Package.Status.ACTIVE
        ]
        if missing_ids or unavailable:
            for package_id in missing_ids | set(unavailable):
                cart.pop(str(package_id), None)
            save_cart(request, cart)
            messages.error(
                request,
                "Некоторые пакеты больше недоступны. Проверьте корзину.",
            )
            return redirect("cart_detail")

        for package_id, quantity in quantities.items():
            package = package_map[package_id]
            if quantity < 1:
                messages.error(request, "Некорректное количество в корзине.")
                return redirect("cart_detail")
            if not package.is_unlimited and quantity > package.available_count:
                messages.error(
                    request,
                    f"Для пакета «{package.name}» доступно только {package.available_count} шт. Обновите корзину.",
                )
                return redirect("cart_detail")

        subtotal = sum(
            (package_map[package_id].price * quantity
             for package_id, quantity in quantities.items()),
            Decimal("0.00"),
        )

        order = Order.objects.create(
            user=request.user,
            status=Order.Status.NEW,
            subtotal=subtotal,
            discount_amount=Decimal("0.00"),
            total_amount=subtotal,
        )

        for package_id, quantity in quantities.items():
            package = package_map[package_id]
            line_total = package.price * quantity
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
            package.allocated_count += quantity
            package.save(update_fields=["allocated_count", "updated_at"])

    save_cart(request, {})
    messages.success(request, "Учебный заказ успешно оформлен.")
    return redirect("order_success", order_number=order.order_number)


@login_required
def order_success(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_number=order_number,
        user=request.user,
    )
    return render(request, "orders/success.html", {"order": order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "orders/history.html", {"orders": orders})
''',
'apps/orders/urls.py': r'''from django.urls import path
from . import views

urlpatterns = [
    path("", views.cart_detail, name="cart_detail"),
    path("add/<int:package_id>/", views.cart_add, name="cart_add"),
    path("update/<int:package_id>/", views.cart_update, name="cart_update"),
    path("remove/<int:package_id>/", views.cart_remove, name="cart_remove"),
    path("clear/", views.cart_clear, name="cart_clear"),
    path("checkout/", views.checkout, name="checkout"),
    path("success/<uuid:order_number>/", views.order_success, name="order_success"),
]
''',
'templates/cart/detail.html': r'''{% extends "base.html" %}
{% load money %}
{% block title %}Корзина — InvestSim{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4">
  <div>
    <h1 class="h2 mb-1">Корзина</h1>
    <p class="text-secondary mb-0">Проверьте выбранные учебные пакеты.</p>
  </div>
  <a href="{% url 'package_list' %}" class="btn btn-outline-secondary">Продолжить выбор</a>
</div>

{% if items %}
<div class="row g-4">
  <div class="col-lg-8">
    <div class="card shadow-sm">
      <div class="table-responsive">
        <table class="table align-middle mb-0">
          <thead class="table-light">
            <tr><th>Пакет</th><th>Цена</th><th style="min-width:150px">Количество</th><th>Сумма</th><th></th></tr>
          </thead>
          <tbody>
            {% for item in items %}
            <tr>
              <td>
                <div class="fw-semibold">{{ item.package.name }}</div>
                <div class="small text-secondary">{{ item.package.duration_days }} дней</div>
                {% if item.is_over_limit %}<div class="small text-danger">Доступно только {{ item.available_count }} шт.</div>{% endif %}
              </td>
              <td>{{ item.package.price|money }}</td>
              <td>
                <form method="post" action="{% url 'cart_update' item.package.id %}" class="d-flex gap-1">
                  {% csrf_token %}
                  <input class="form-control form-control-sm" type="number" name="quantity" min="0" value="{{ item.quantity }}" style="max-width:85px" aria-label="Количество">
                  <button class="btn btn-sm btn-outline-primary" type="submit">Ок</button>
                </form>
                <div class="small text-secondary mt-1">0 — удалить</div>
              </td>
              <td class="fw-semibold text-nowrap">{{ item.line_total|money }}</td>
              <td>
                <form method="post" action="{% url 'cart_remove' item.package.id %}">
                  {% csrf_token %}
                  <button class="btn btn-sm btn-outline-danger" type="submit" aria-label="Удалить">×</button>
                </form>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    <form method="post" action="{% url 'cart_clear' %}" class="mt-3">
      {% csrf_token %}
      <button class="btn btn-link text-danger px-0" type="submit">Очистить корзину</button>
    </form>
  </div>
  <div class="col-lg-4">
    <div class="card shadow-sm">
      <div class="card-body">
        <h2 class="h5">Ваш заказ</h2>
        <div class="d-flex justify-content-between py-3 border-bottom"><span>Позиций</span><strong>{{ items|length }}</strong></div>
        <div class="d-flex justify-content-between py-3"><span>Итого</span><strong class="fs-4">{{ total|money }}</strong></div>
        {% if user.is_authenticated %}
          <form method="post" action="{% url 'checkout' %}">
            {% csrf_token %}
            <button class="btn btn-primary btn-lg w-100" type="submit" {% if has_over_limit %}disabled{% endif %}>Оформить заказ</button>
          </form>
        {% else %}
          <a class="btn btn-primary btn-lg w-100" href="{% url 'login' %}?next={% url 'cart_detail' %}">Войти для оформления</a>
          <p class="small text-secondary mt-2 mb-0">Для оформления заказа необходимо войти в аккаунт.</p>
        {% endif %}
        <p class="small text-secondary mt-3 mb-0">Учебный заказ: реальные платежи не выполняются.</p>
      </div>
    </div>
  </div>
</div>
{% else %}
<div class="card card-body text-center py-5">
  <div class="display-4 mb-3">🛒</div>
  <h2 class="h4">Корзина пока пуста</h2>
  <p class="text-secondary">Перейдите в каталог и добавьте понравившиеся пакеты.</p>
  <a class="btn btn-primary align-self-center" href="{% url 'package_list' %}">Перейти к пакетам</a>
</div>
{% endif %}
{% endblock %}
''',
'templates/orders/success.html': r'''{% extends "base.html" %}
{% load money %}
{% block title %}Заказ оформлен — InvestSim{% endblock %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-lg-8">
    <div class="card shadow-sm">
      <div class="card-body p-4 p-md-5">
        <div class="text-success display-5 mb-3">✓</div>
        <h1 class="h2">Учебный заказ оформлен</h1>
        <p class="text-secondary">Заказ сохранён в системе. Реальная оплата не производилась.</p>
        <div class="alert alert-light border">
          <div class="small text-secondary">Номер заказа</div>
          <div class="fw-semibold text-break">{{ order.order_number }}</div>
          <div class="small text-secondary mt-2">Статус: {{ order.get_status_display }}</div>
        </div>
        <h2 class="h5 mt-4">Состав заказа</h2>
        {% for item in order.items.all %}
        <div class="d-flex justify-content-between gap-3 border-bottom py-2">
          <div>{{ item.package_name_snapshot }} × {{ item.quantity }}</div>
          <strong class="text-nowrap">{{ item.net_amount_snapshot|money }}</strong>
        </div>
        {% endfor %}
        <div class="d-flex justify-content-between fs-5 mt-3">
          <strong>Итого</strong><strong>{{ order.total_amount|money }}</strong>
        </div>
        <div class="d-flex flex-wrap gap-2 mt-4">
          <a href="{% url 'order_history' %}" class="btn btn-primary">Мои заказы</a>
          <a href="{% url 'package_list' %}" class="btn btn-outline-secondary">Вернуться в каталог</a>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
''',
'templates/orders/history.html': r'''{% extends "base.html" %}
{% load money %}
{% block title %}Мои заказы — InvestSim{% endblock %}
{% block content %}
<h1 class="h2 mb-4">Мои заказы</h1>
{% for order in orders %}
<div class="card shadow-sm mb-3">
  <div class="card-body">
    <div class="d-flex justify-content-between flex-wrap gap-2">
      <div>
        <div class="small text-secondary">Заказ от {{ order.created_at|date:"d.m.Y H:i" }}</div>
        <div class="fw-semibold text-break">№ {{ order.order_number }}</div>
      </div>
      <div class="text-md-end">
        <div class="fw-semibold">{{ order.total_amount|money }}</div>
        <span class="badge text-bg-secondary">{{ order.get_status_display }}</span>
      </div>
    </div>
    <hr>
    {% for item in order.items.all %}
      <div class="d-flex justify-content-between gap-3 small py-1">
        <span>{{ item.package_name_snapshot }} × {{ item.quantity }}</span>
        <span class="text-nowrap">{{ item.net_amount_snapshot|money }}</span>
      </div>
    {% endfor %}
  </div>
</div>
{% empty %}
<div class="alert alert-info">У вас пока нет оформленных заказов.</div>
<a href="{% url 'package_list' %}" class="btn btn-primary">Выбрать пакет</a>
{% endfor %}
{% endblock %}
''',
}

for relative, content in files.items():
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

# Add cart routes and order history route without overwriting other URL patterns.
urls_path = ROOT / 'config/urls.py'
urls = urls_path.read_text(encoding='utf-8')
if 'from apps.orders import views as order_views' not in urls:
    urls = urls.replace('from django.urls import include, path\n', 'from django.urls import include, path\nfrom apps.orders import views as order_views\n')
if 'path("cart/", include("apps.orders.urls"))' not in urls:
    urls = urls.replace('    path("accounts/", include("apps.users.urls")),\n', '    path("accounts/", include("apps.users.urls")),\n    path("cart/", include("apps.orders.urls")),\n    path("orders/", order_views.order_history, name="order_history"),\n')
urls_path.write_text(urls, encoding='utf-8')

# Expose a cart item count to every template.
context_path = ROOT / 'config/context_processors.py'
context_path.write_text('''from django.conf import settings


def project_settings(request):
    cart = request.session.get("investment_cart", {})
    if not isinstance(cart, dict):
        cart = {}
    count = 0
    for quantity in cart.values():
        try:
            count += max(0, int(quantity))
        except (TypeError, ValueError):
            continue
    return {
        "DEFAULT_CURRENCY": getattr(settings, "DEFAULT_CURRENCY", "RUB"),
        "cart_count": count,
    }
''', encoding='utf-8')

# Add cart and order links to the main navigation.
base_path = ROOT / 'templates/base.html'
base = base_path.read_text(encoding='utf-8')
if "url 'cart_detail'" not in base:
    marker = '          <a class="nav-link" href="{% url \'package_list\' %}">Пакеты</a>\n'
    insert = marker + '          <a class="nav-link" href="{% url \'cart_detail\' %}">Корзина <span class="badge text-bg-primary">{{ cart_count }}</span></a>\n          {% if user.is_authenticated %}<a class="nav-link" href="{% url \'order_history\' %}">Мои заказы</a>{% endif %}\n'
    if marker not in base:
        raise SystemExit('Не найден пункт «Пакеты» в templates/base.html; автоматическая установка остановлена без изменения этого файла.')
    base = base.replace(marker, insert)
base_path.write_text(base, encoding='utf-8')

# Add an add-to-cart form to catalog cards and home page cards.
for relative in ['templates/storefront/package_list.html', 'templates/storefront/home.html']:
    path = ROOT / relative
    text = path.read_text(encoding='utf-8')
    if "url 'cart_add' package.id" not in text:
        marker = '<a class="btn btn-outline-primary" href="{% url \'package_detail\' package.slug %}">Подробнее</a>'
        replacement = marker + '''
            <form method="post" action="{% url 'cart_add' package.id %}" class="mt-2">
              {% csrf_token %}
              <input type="hidden" name="quantity" value="1">
              <button class="btn btn-primary w-100" type="submit">В корзину</button>
            </form>'''
        if marker not in text:
            raise SystemExit(f'Не найдена кнопка «Подробнее» в {relative}; автоматическая установка остановлена.')
        text = text.replace(marker, replacement)
    path.write_text(text, encoding='utf-8')

# Add add-to-cart form to package detail page.
detail_path = ROOT / 'templates/storefront/package_detail.html'
detail = detail_path.read_text(encoding='utf-8')
if "url 'cart_add' package.id" not in detail:
    marker = '    <div class="alert alert-warning mt-3 small">Покупка и доходность в проекте моделируются в учебных целях. Реальные денежные операции не выполняются.</div>'
    replacement = '''    <form method="post" action="{% url 'cart_add' package.id %}" class="mt-3">
      {% csrf_token %}
      <input type="hidden" name="quantity" value="1">
      <button class="btn btn-primary btn-lg w-100" type="submit">Добавить в корзину</button>
    </form>
''' + marker
    if marker not in detail:
        raise SystemExit('Не найден дисклеймер в package_detail.html; автоматическая установка остановлена.')
    detail = detail.replace(marker, replacement)
detail_path.write_text(detail, encoding='utf-8')

print('Корзина, оформление учебного заказа и история заказов установлены.')
print('Изменены/созданы файлы:')
for relative in files:
    print(' -', relative)
print(' - config/urls.py')
print(' - config/context_processors.py')
print(' - templates/base.html')
print(' - templates/storefront/package_list.html')
print(' - templates/storefront/home.html')
print(' - templates/storefront/package_detail.html')
