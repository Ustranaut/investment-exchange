from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("packages/", views.package_list, name="package_list"),
    path("packages/<slug:slug>/", views.package_detail, name="package_detail"),
]
