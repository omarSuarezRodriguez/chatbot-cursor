"""Panel operative preferences via accounts.DashboardSettings (PostgreSQL)."""

from __future__ import annotations

from typing import Any, Dict

from apps.accounts.models import DashboardSettings

DEFAULTS: Dict[str, str] = {
    "default_order_status_filter": "",
    "orders_per_page": "20",
    "show_cancelled_orders": "1",
    "panel_notes": "",
}

BOOL_KEYS = frozenset({"show_cancelled_orders"})


def load_panel_settings() -> Dict[str, Any]:
    values = dict(DEFAULTS)
    for row in DashboardSettings.objects.filter(key__in=DEFAULTS):
        values[row.key] = row.value
    return {
        "default_order_status_filter": values["default_order_status_filter"],
        "orders_per_page": int(values.get("orders_per_page") or 20),
        "show_cancelled_orders": values.get("show_cancelled_orders", "1") == "1",
        "panel_notes": values.get("panel_notes", ""),
    }


def save_panel_settings(data: Dict[str, Any]) -> None:
    payload = {
        "default_order_status_filter": str(data.get("default_order_status_filter", "")),
        "orders_per_page": str(data.get("orders_per_page", 20)),
        "show_cancelled_orders": "1" if data.get("show_cancelled_orders") else "0",
        "panel_notes": str(data.get("panel_notes", "")),
    }
    for key, value in payload.items():
        DashboardSettings.objects.update_or_create(
            key=key,
            defaults={"value": value},
        )
