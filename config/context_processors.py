from django.conf import settings

def project_settings(request):
    return {"DEFAULT_CURRENCY": getattr(settings, "DEFAULT_CURRENCY", "RUB")}
