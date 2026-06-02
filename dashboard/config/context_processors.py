from django.conf import settings


def dashboard_flags(request):
    return {
        "dashboard_writes_enabled": getattr(settings, "DASHBOARD_ENABLE_WRITES", False),
    }
