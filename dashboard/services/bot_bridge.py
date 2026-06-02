"""Safe dashboard writes via existing bot services (no Flask endpoints)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

WA_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_+\-]{3,64}$")
ORDER_STATUSES = frozenset({"pending", "confirmed", "delivered", "cancelled"})


@dataclass(frozen=True)
class WriteResult:
    ok: bool
    message: str
    already_confirmed: bool = False
    entity_id: str = ""


ConfirmOrderResult = WriteResult


def writes_enabled() -> bool:
    return bool(getattr(settings, "DASHBOARD_ENABLE_WRITES", False))


def _disabled() -> WriteResult:
    return WriteResult(
        ok=False,
        message="Las escrituras del panel están deshabilitadas (DASHBOARD_ENABLE_WRITES=0).",
    )


def _bot_services():
    from app.config import GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_ID
    from app.integrations.google_sheets import get_google_sheets_client
    from app.services.admin_service import AdminService
    from app.services.menu_service import MenuService
    from app.services.order_service import OrderService
    from app.services.user_service import UserService

    sheets = get_google_sheets_client(
        GOOGLE_SHEETS_CREDENTIALS_PATH,
        GOOGLE_SPREADSHEET_ID,
    )
    menu_service = MenuService(sheets)
    order_service = OrderService(sheets, menu_service)
    admin_service = AdminService(sheets, order_service)
    user_service = UserService(sheets)
    return sheets, menu_service, order_service, admin_service, user_service


def _validate_wa_id(wa_id: str) -> Optional[str]:
    wa_id = str(wa_id).strip()
    if not wa_id:
        return "El WA ID es obligatorio."
    if not WA_ID_PATTERN.match(wa_id):
        return "WA ID inválido (3–64 caracteres alfanuméricos, _, +, -)."
    return None


def confirm_order(order_id: str) -> ConfirmOrderResult:
    """Confirm a pending order (Sheets + optional Twilio to customer)."""
    if not writes_enabled():
        return _disabled()

    order_id = order_id.strip().upper()
    if not order_id:
        return WriteResult(ok=False, message="ID de pedido vacío.")

    _, _, order_service, admin_service, _ = _bot_services()
    order = order_service.get_order(order_id)
    if not order:
        return WriteResult(ok=False, message=f"No encontré el pedido {order_id}.")

    if str(order.get("status", "")).lower() == "confirmed":
        return WriteResult(
            ok=False,
            message=f"El pedido {order_id} ya estaba confirmado.",
            already_confirmed=True,
            entity_id=order_id,
        )

    if not order_service.confirm_order(order_id):
        return WriteResult(
            ok=False,
            message=f"No pude actualizar el pedido {order_id}.",
            entity_id=order_id,
        )

    admin_service.notify_customer_order_confirmed(order_id, order.get("wa_id", ""))
    return WriteResult(
        ok=True,
        message=f"Pedido {order_id} confirmado correctamente.",
        entity_id=order_id,
    )


def set_menu_item_unavailable(item_id: str) -> Tuple[bool, str]:
    """Mark a menu item as not available (local cache + Sheet MENU)."""
    return set_menu_item_availability(item_id, False)


def set_menu_item_availability(item_id: str, disponible: bool) -> Tuple[bool, str]:
    if not writes_enabled():
        return False, _disabled().message

    item_id = str(item_id).strip()
    if not item_id:
        return False, "ID de plato vacío."

    _, menu_service, _, _, _ = _bot_services()
    if menu_service.set_availability(item_id, disponible):
        state = "disponible" if disponible else "no disponible"
        return True, f"Plato {item_id} marcado como {state}."
    return False, f"No encontré el plato {item_id} en el menú."


def save_menu_item(
    item_id: str,
    nombre: str,
    precio: float,
    categoria: str,
    disponible: bool = True,
    *,
    is_new: bool = False,
) -> WriteResult:
    if not writes_enabled():
        return _disabled()

    item_id = str(item_id).strip()
    nombre = str(nombre).strip()
    categoria = str(categoria).strip() or "General"
    if not item_id:
        return WriteResult(ok=False, message="El ID del plato es obligatorio.")
    if not nombre:
        return WriteResult(ok=False, message="El nombre es obligatorio.")
    if precio <= 0:
        return WriteResult(ok=False, message="El precio debe ser mayor que 0.")

    _, menu_service, _, _, _ = _bot_services()
    menu = menu_service.sheets.get_menu()
    exists = any(str(i.get("id", "")).strip() == item_id for i in menu)
    if is_new and exists:
        return WriteResult(
            ok=False,
            message=f"Ya existe un plato con ID {item_id}.",
            entity_id=item_id,
        )
    if not is_new and not exists:
        return WriteResult(
            ok=False,
            message=f"No encontré el plato {item_id}.",
            entity_id=item_id,
        )

    if menu_service.save_item(item_id, nombre, precio, categoria, disponible):
        verb = "creado" if is_new else "actualizado"
        return WriteResult(
            ok=True,
            message=f"Plato {item_id} {verb} correctamente.",
            entity_id=item_id,
        )
    return WriteResult(
        ok=False,
        message=f"No pude guardar el plato {item_id}.",
        entity_id=item_id,
    )


def delete_menu_item(item_id: str, *, hard: bool = False) -> WriteResult:
    if not writes_enabled():
        return _disabled()

    item_id = str(item_id).strip()
    if not item_id:
        return WriteResult(ok=False, message="ID de plato vacío.")

    _, menu_service, _, _, _ = _bot_services()
    if menu_service.remove_item(item_id, hard=hard):
        mode = "eliminado" if hard else "dado de baja (no disponible)"
        return WriteResult(
            ok=True,
            message=f"Plato {item_id} {mode}.",
            entity_id=item_id,
        )
    return WriteResult(
        ok=False,
        message=f"No encontré el plato {item_id}.",
        entity_id=item_id,
    )


def create_manual_order(
    wa_id: str,
    items: List[Dict[str, Any]],
    customer_name: str = "",
    address: str = "",
    delivery_type: str = "",
) -> WriteResult:
    if not writes_enabled():
        return _disabled()

    wa_error = _validate_wa_id(wa_id)
    if wa_error:
        return WriteResult(ok=False, message=wa_error)
    if not items:
        return WriteResult(ok=False, message="El pedido debe tener al menos un ítem.")

    _, _, order_service, _, _ = _bot_services()
    order_id, total = order_service.save_order(
        wa_id=wa_id.strip(),
        items=items,
        customer_name=customer_name.strip(),
        address=address.strip(),
        delivery_type=delivery_type.strip(),
    )
    return WriteResult(
        ok=True,
        message=f"Pedido {order_id} creado (total {total:.2f} €).",
        entity_id=order_id,
    )


def update_order_status(order_id: str, status: str) -> WriteResult:
    if not writes_enabled():
        return _disabled()

    order_id = order_id.strip().upper()
    status = str(status).strip().lower()
    if status not in ORDER_STATUSES:
        return WriteResult(ok=False, message=f"Estado inválido: {status}.")

    _, _, order_service, _, _ = _bot_services()
    if not order_service.get_order(order_id):
        return WriteResult(ok=False, message=f"No encontré el pedido {order_id}.")

    if not order_service.update_order_status(order_id, status):
        return WriteResult(
            ok=False,
            message=f"No pude actualizar el pedido {order_id}.",
            entity_id=order_id,
        )
    return WriteResult(
        ok=True,
        message=f"Pedido {order_id} → {status}.",
        entity_id=order_id,
    )


def cancel_order(order_id: str) -> WriteResult:
    return update_order_status(order_id.strip().upper(), "cancelled")


def update_order_items(order_id: str, items: List[Dict[str, Any]]) -> WriteResult:
    if not writes_enabled():
        return _disabled()

    order_id = order_id.strip().upper()
    if not items:
        return WriteResult(ok=False, message="El pedido debe tener al menos un ítem.")

    _, _, order_service, _, _ = _bot_services()
    order = order_service.get_order(order_id)
    if not order:
        return WriteResult(ok=False, message=f"No encontré el pedido {order_id}.")
    if str(order.get("status", "")).lower() == "cancelled":
        return WriteResult(
            ok=False,
            message="No se pueden editar ítems de un pedido cancelado.",
            entity_id=order_id,
        )

    if not order_service.update_order(order_id, items=items):
        return WriteResult(
            ok=False,
            message=f"No pude actualizar los ítems del pedido {order_id}.",
            entity_id=order_id,
        )
    total = order_service.cart_total(items)
    return WriteResult(
        ok=True,
        message=f"Ítems actualizados (nuevo total {total:.2f} €).",
        entity_id=order_id,
    )


def save_customer(
    wa_id: str,
    name: str = "",
    notes: str = "",
    *,
    is_new: bool = False,
) -> WriteResult:
    if not writes_enabled():
        return _disabled()

    wa_id = wa_id.strip()
    wa_error = _validate_wa_id(wa_id)
    if wa_error:
        return WriteResult(ok=False, message=wa_error)
    if not str(name).strip():
        return WriteResult(ok=False, message="El nombre es obligatorio.")

    _, _, _, _, user_service = _bot_services()
    existing = user_service.get_profile(wa_id)
    if is_new and existing.get("wa_id"):
        return WriteResult(
            ok=False,
            message=f"Ya existe un cliente con WA ID {wa_id}.",
            entity_id=wa_id,
        )
    if not is_new and not existing.get("wa_id"):
        return WriteResult(
            ok=False,
            message=f"No encontré el cliente {wa_id}.",
            entity_id=wa_id,
        )

    user_service.save_customer(wa_id, name=name.strip(), notes=notes.strip())
    verb = "creado" if is_new else "actualizado"
    return WriteResult(
        ok=True,
        message=f"Cliente {wa_id} {verb} correctamente.",
        entity_id=wa_id,
    )


def delete_customer(wa_id: str) -> WriteResult:
    if not writes_enabled():
        return _disabled()

    wa_id = wa_id.strip()
    if not wa_id:
        return WriteResult(ok=False, message="WA ID vacío.")

    _, _, _, _, user_service = _bot_services()
    if not user_service.get_profile(wa_id).get("wa_id"):
        return WriteResult(ok=False, message=f"No encontré el cliente {wa_id}.")

    if not user_service.delete_customer(wa_id):
        return WriteResult(
            ok=False,
            message=f"No pude eliminar el cliente {wa_id}.",
            entity_id=wa_id,
        )
    return WriteResult(
        ok=True,
        message=f"Cliente {wa_id} eliminado del panel.",
        entity_id=wa_id,
    )


def parse_order_items_json(raw: str) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """Parse dashboard JSON items field into bot cart format."""
    raw = (raw or "").strip()
    if not raw:
        return None, "Los ítems son obligatorios."
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"JSON inválido: {exc}"
    if not isinstance(data, list):
        return None, "El JSON debe ser una lista de ítems."
    items: List[Dict[str, Any]] = []
    for idx, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            return None, f"Ítem #{idx}: debe ser un objeto."
        product = str(row.get("product") or row.get("nombre") or "").strip()
        if not product:
            return None, f"Ítem #{idx}: falta product/nombre."
        try:
            qty = int(row.get("qty", 1))
            unit_price = float(row.get("unit_price", row.get("precio", 0)))
        except (TypeError, ValueError):
            return None, f"Ítem #{idx}: qty o precio inválido."
        if qty < 1:
            return None, f"Ítem #{idx}: qty debe ser ≥ 1."
        if unit_price <= 0:
            return None, f"Ítem #{idx}: precio debe ser > 0."
        subtotal = round(qty * unit_price, 2)
        items.append(
            {
                "product": product,
                "qty": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
    return items, ""
