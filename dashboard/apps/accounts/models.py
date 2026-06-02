from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Panel audit trail only; business data stays in Sheets / data/*.json."""

    action = models.CharField(max_length=64)
    entity = models.CharField(max_length=64, blank=True)
    entity_id = models.CharField(max_length=128, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity} {self.entity_id}".strip()


class DashboardSettings(models.Model):
    """Key-value UI / panel metadata (not bot RESTAURANT_NAME unless synced explicitly)."""

    key = models.CharField(max_length=128, unique=True)
    value = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "dashboard setting"
        verbose_name_plural = "dashboard settings"

    def __str__(self) -> str:
        return self.key
