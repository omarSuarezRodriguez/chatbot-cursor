from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from .models import AuditLog


def log_audit(
    request: HttpRequest,
    *,
    action: str,
    entity: str = "",
    entity_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    return AuditLog.objects.create(
        action=action,
        entity=entity,
        entity_id=entity_id,
        user=user,
        metadata=metadata or {},
    )
