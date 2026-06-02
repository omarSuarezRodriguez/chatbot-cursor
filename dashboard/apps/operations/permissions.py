"""Dashboard role checks: dashboard_operator vs dashboard_admin."""

from __future__ import annotations

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

GROUP_OPERATOR = "dashboard_operator"
GROUP_ADMIN = "dashboard_admin"


def user_is_dashboard_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=GROUP_ADMIN).exists()


def user_is_dashboard_operator(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return (
        user.groups.filter(name__in=[GROUP_OPERATOR, GROUP_ADMIN]).exists()
    )


class OperatorRequiredMixin(AccessMixin):
    """Read + operational writes (orders, clients, menu availability)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not user_is_dashboard_operator(request.user):
            raise PermissionDenied("Se requiere rol operador o admin del panel.")
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(AccessMixin):
    """Full CRUD: menu create/delete, client delete, panel settings."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not user_is_dashboard_admin(request.user):
            raise PermissionDenied("Se requiere rol admin del panel.")
        return super().dispatch(request, *args, **kwargs)
