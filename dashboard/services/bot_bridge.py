"""Safe dashboard writes via existing bot services (no Flask endpoints)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from django.conf import settings


@dataclass(frozen=True)
class ConfirmOrderResult:
    ok: bool
    message: str
    already_confirmed: bool = False


def writes_enabled() -> bool:
    return bool(getattr(settings, "DASHBOARD_ENABLE_WRITES", False))


def _bot_services():
    from app.config import GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_ID
    from app.integrations.google_sheets import get_google_sheets_client
    from app.services.admin_service import AdminService
    from app.services.menu_service import MenuService
    from app.services.order_service import OrderService

    sheets = get_google_sheets_client(
        GOOGLE_SHEETS_CREDENTIALS_PATH,
        GOOGLE_SPREADSHEET_ID,
    )
    menu_service = MenuService(sheets)
    order_service = OrderService(sheets, menu_service)
    admin_service = AdminService(sheets, order_service)
    return sheets, order_service, admin_service


def confirm_order(order_id: str) -> ConfirmOrderResult:
    """Confirm a pending order (Sheets + optional Twilio to customer)."""
    if not writes_enabled():
        return ConfirmOrderResult(
            ok=False,
            message="Las escrituras del panel están deshabilitadas (DASHBOARD_ENABLE_WRITES=0).",
        )

    order_id = order_id.strip().upper()
    if not order_id:
        return ConfirmOrderResult(ok=False, message="ID de pedido vacío.")

    _, order_service, admin_service = _bot_services()
    order = order_service.get_order(order_id)
    if not order:
        return ConfirmOrderResult(ok=False, message=f"No encontré el pedido {order_id}.")

    if str(order.get("status", "")).lower() == "confirmed":
        return ConfirmOrderResult(
            ok=False,
            message=f"El pedido {order_id} ya estaba confirmado.",
            already_confirmed=True,
        )

    if not order_service.confirm_order(order_id):
        return ConfirmOrderResult(
            ok=False,
            message=f"No pude actualizar el pedido {order_id}.",
        )

    admin_service.notify_customer_order_confirmed(order_id, order.get("wa_id", ""))
    return ConfirmOrderResult(
        ok=True,
        message=f"Pedido {order_id} confirmado correctamente.",
    )


def set_menu_item_unavailable(item_id: str) -> Tuple[bool, str]:
    """Mark a menu item as not available (local cache + Sheet MENU)."""
    if not writes_enabled():
        return (
            False,
            "Las escrituras del panel están deshabilitadas (DASHBOARD_ENABLE_WRITES=0).",
        )

    item_id = str(item_id).strip()
    if not item_id:
        return False, "ID de plato vacío."

    sheets, _, _ = _bot_services()
    if sheets.set_menu_item_availability(item_id, False):
        return True, f"Plato {item_id} marcado como no disponible."
    return False, f"No encontré el plato {item_id} en el menú."
