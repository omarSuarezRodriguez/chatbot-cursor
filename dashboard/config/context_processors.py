from django.conf import settings


def dashboard_flags(request):
    return {
        "dashboard_writes_enabled": getattr(settings, "DASHBOARD_ENABLE_WRITES", False),
    }


def dashboard_roles(request):
    user = request.user
    if not user.is_authenticated:
        return {"is_dashboard_admin": False, "is_dashboard_operator": False}
    from apps.operations.permissions import (
        user_is_dashboard_admin,
        user_is_dashboard_operator,
    )

    return {
        "is_dashboard_admin": user_is_dashboard_admin(user),
        "is_dashboard_operator": user_is_dashboard_operator(user),
    }
