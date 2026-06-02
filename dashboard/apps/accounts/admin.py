from django.contrib import admin

from .models import AuditLog, DashboardSettings


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "action", "entity", "entity_id", "user")
    list_filter = ("action", "entity")
    search_fields = ("entity_id", "user__username")
    readonly_fields = ("timestamp", "action", "entity", "entity_id", "user", "metadata")


@admin.register(DashboardSettings)
class DashboardSettingsAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "updated_at")
    search_fields = ("key",)
