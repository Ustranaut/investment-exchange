from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.packages.models import Package
from apps.orders.models import Order


def staff_role_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        allowed = (
            request.user.is_superuser
            or request.user.role in ("manager", "superadmin")
        )
        if not allowed:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_role_required
def index(request):
    User = get_user_model()
    context = {
        "packages_count": Package.objects.count(),
        "active_packages_count": Package.objects.filter(status=Package.Status.ACTIVE).count(),
        "orders_count": Order.objects.count(),
        "users_count": User.objects.count(),
        "recent_orders": Order.objects.select_related("user")[:8],
    }
    return render(request, "admin_panel/dashboard.html", context)
