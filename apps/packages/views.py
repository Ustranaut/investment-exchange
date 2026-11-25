from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from .models import Package


def home(request):
    packages = Package.objects.filter(status=Package.Status.ACTIVE)[:3]
    return render(request, "storefront/home.html", {"packages": packages})


def package_list(request):
    query = request.GET.get("q", "").strip()
    packages = Package.objects.filter(status=Package.Status.ACTIVE)
    if query:
        packages = packages.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, "storefront/package_list.html", {
        "packages": packages,
        "query": query,
    })


def package_detail(request, slug):
    package = get_object_or_404(Package, slug=slug, status=Package.Status.ACTIVE)
    return render(request, "storefront/package_detail.html", {"package": package})
