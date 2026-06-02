"""Safe dashboard writes via existing bot services (no Flask endpoints)."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

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
    try:
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
    except Exception:
        import gspread
        from google.oauth2.service_account import Credentials

        class _StandaloneSheets:
            def __init__(self) -> None:
                spreadsheet_id = os.environ.get("GOOGLE_SPREADSHEET_ID", "").strip()
                json_blob = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
                creds_path = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_PATH", "").strip()
                default_creds = settings.PROJECT_ROOT / "credentials" / "google-service-account.json"
                if not spreadsheet_id or (not json_blob and not creds_path and not default_creds.is_file()):
                    raise RuntimeError("Missing Google Sheets credentials in dashboard service")
                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
                if json_blob:
                    creds = Credentials.from_service_account_info(
                        json.loads(json_blob),
                        scopes=scopes,
                    )
                else:
                    resolved_path = Path(creds_path) if creds_path else default_creds
                    creds = Credentials.from_service_account_file(
                        str(resolved_path),
                        scopes=scopes,
                    )
                client = gspread.authorize(creds)
                self.spreadsheet = client.open_by_key(spreadsheet_id)

            def ws(self, name: str):
                return self.spreadsheet.worksheet(name)

            def get_menu(self) -> List[Dict[str, Any]]:
                menu = []
                for row in self.ws("MENU").get_all_records():
                    if not row.get("nombre"):
                        continue
                    try:
                        precio = float(row.get("precio", 0) or 0)
                    except (TypeError, ValueError):
                        precio = 0.0
                    disp = str(row.get("disponible", "true")).strip().lower()
                    menu.append(
                        {
                            "id": str(row.get("id", "")).strip(),
                            "nombre": str(row.get("nombre", "")).strip(),
                            "precio": precio,
                            "categoria": str(row.get("categoria", "")).strip(),
                            "disponible": disp in {"1", "true", "si", "sí", "yes", "y"},
                        }
                    )
                return menu

        class _StandaloneMenuService:
            def __init__(self, sheets: _StandaloneSheets) -> None:
                self.sheets = sheets

            def set_availability(self, item_id: str, disponible: bool) -> bool:
                ws = self.sheets.ws("MENU")
                cell = ws.find(item_id, in_column=1)
                if not cell:
                    return False
                ws.update_cell(cell.row, 5, "TRUE" if disponible else "FALSE")
                return True

            def save_item(
                self, item_id: str, nombre: str, precio: float, categoria: str, disponible: bool
            ) -> bool:
                ws = self.sheets.ws("MENU")
                try:
                    cell = ws.find(item_id, in_column=1)
                except Exception:
                    cell = None
                row = [item_id, nombre, precio, categoria, "TRUE" if disponible else "FALSE"]
                if cell:
                    ws.update(f"A{cell.row}:E{cell.row}", [row])
                else:
                    ws.append_row(row)
                return True

            def remove_item(self, item_id: str, hard: bool = False) -> bool:
                ws = self.sheets.ws("MENU")
                cell = ws.find(item_id, in_column=1)
                if not cell:
                    return False
                if hard:
                    ws.delete_rows(cell.row)
                else:
                    ws.update_cell(cell.row, 5, "FALSE")
                return True

        class _StandaloneOrderService:
            def __init__(self, sheets: _StandaloneSheets, menu_service: _StandaloneMenuService) -> None:
                self.sheets = sheets
                self.menu_service = menu_service

            def _orders_ws(self):
                return self.sheets.ws("ORDERS")

            def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
                ws = self._orders_ws()
                for row in ws.get_all_records():
                    if str(row.get("order_id", "")).strip().upper() == order_id.upper():
                        try:
                            items = json.loads(row.get("items") or "[]")
                        except Exception:
                            items = []
                        return {
                            "order_id": str(row.get("order_id", "")).strip().upper(),
                            "wa_id": str(row.get("wa_id", "")),
                            "items": items,
                            "total": float(row.get("total", 0) or 0),
                            "status": str(row.get("status", "pending")).lower(),
                            "timestamp": str(row.get("timestamp", "")),
                            "customer_name": str(row.get("customer_name", "")),
                            "address": str(row.get("address", "")),
                            "delivery_type": str(row.get("delivery_type", "")),
                        }
                return None

            def _find_order_rows(self, order_id: str) -> List[int]:
                ws = self._orders_ws()
                needle = order_id.upper().strip()
                rows = ws.col_values(1)
                hits: List[int] = []
                for idx, value in enumerate(rows, start=1):
                    if idx == 1:
                        continue
                    if str(value).strip().upper() == needle:
                        hits.append(idx)
                return hits

            def confirm_order(self, order_id: str) -> bool:
                return self.update_order_status(order_id, "confirmed")

            def update_order_status(self, order_id: str, status: str) -> bool:
                rows = self._find_order_rows(order_id)
                if not rows:
                    return False
                ws = self._orders_ws()
                for row in rows:
                    ws.update_cell(row, 5, status)
                return True

            def update_order(self, order_id: str, items: Optional[List[Dict[str, Any]]] = None) -> bool:
                rows = self._find_order_rows(order_id)
                if not rows:
                    return False
                if items is not None:
                    total = self.cart_total(items)
                    ws = self._orders_ws()
                    payload = [json.dumps(items, ensure_ascii=False), total]
                    for row in rows:
                        ws.update(f"C{row}:D{row}", [payload])
                return True

            def cart_total(self, items: List[Dict[str, Any]]) -> float:
                total = 0.0
                for item in items:
                    try:
                        total += float(item.get("subtotal") or 0)
                    except (TypeError, ValueError):
                        pass
                return round(total, 2)

            def save_order(
                self,
                wa_id: str,
                items: List[Dict[str, Any]],
                customer_name: str = "",
                address: str = "",
                delivery_type: str = "",
            ) -> Tuple[str, float]:
                order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
                total = self.cart_total(items)
                self._orders_ws().append_row(
                    [
                        order_id,
                        wa_id,
                        json.dumps(items, ensure_ascii=False),
                        total,
                        "pending",
                        datetime.utcnow().isoformat(),
                        customer_name,
                        address,
                        delivery_type,
                    ]
                )
                return order_id, total

        class _StandaloneAdminService:
            def notify_customer_order_confirmed(self, _order_id: str, _wa_id: str) -> None:
                return

        class _StandaloneUserService:
            def __init__(self, sheets: _StandaloneSheets) -> None:
                self.sheets = sheets

            def _users_ws(self):
                return self.sheets.ws("USERS")

            def get_profile(self, wa_id: str) -> Dict[str, Any]:
                ws = self._users_ws()
                for row in ws.get_all_records():
                    if str(row.get("wa_id", "")).strip() == wa_id:
                        return {
                            "wa_id": wa_id,
                            "name": str(row.get("name", "")),
                            "notes": str(row.get("notes", "")),
                        }
                return {}

            def save_customer(self, wa_id: str, name: str = "", notes: str = "") -> None:
                ws = self._users_ws()
                try:
                    cell = ws.find(wa_id, in_column=1)
                except Exception:
                    cell = None
                if cell:
                    ws.update(f"B{cell.row}:C{cell.row}", [[name, notes]])
                else:
                    ws.append_row([wa_id, name, "", "", "", datetime.utcnow().isoformat()])

            def delete_customer(self, wa_id: str) -> bool:
                ws = self._users_ws()
                try:
                    cell = ws.find(wa_id, in_column=1)
                except Exception:
                    cell = None
                if not cell:
                    return False
                ws.delete_rows(cell.row)
                return True

        sheets = _StandaloneSheets()
        menu_service = _StandaloneMenuService(sheets)
        order_service = _StandaloneOrderService(sheets, menu_service)
        admin_service = _StandaloneAdminService()
        user_service = _StandaloneUserService(sheets)
        return sheets, menu_service, order_service, admin_service, user_service


def _format_whatsapp_address(number: str) -> str:
    stripped = number.replace("whatsapp:", "").strip()
    digits = "".join(ch for ch in stripped if ch.isdigit())
    if digits and not stripped.startswith("+"):
        stripped = f"+{digits}"
    return f"whatsapp:{stripped}"


def _twilio_credentials() -> Tuple[str, str, str]:
    """Load Twilio credentials with app.config precedence."""
    try:
        from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM

        account_sid = (TWILIO_ACCOUNT_SID or "").strip()
        auth_token = (TWILIO_AUTH_TOKEN or "").strip()
        from_number = (TWILIO_WHATSAPP_FROM or "").strip()
    except Exception:
        account_sid = ""
        auth_token = ""
        from_number = ""

    if not account_sid:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    if not auth_token:
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    if not from_number:
        from_number = os.environ.get("TWILIO_WHATSAPP_FROM", "").strip()
    return account_sid, auth_token, from_number


def _send_whatsapp(to_number: str, body: str) -> bool:
    account_sid, auth_token, from_number = _twilio_credentials()
    if not (account_sid and auth_token and from_number):
        logger.info("Twilio not configured; skipping customer notify.")
        return False
    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        to = _format_whatsapp_address(to_number)
        from_ = _format_whatsapp_address(from_number)
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
        if not from_.startswith("whatsapp:"):
            from_ = f"whatsapp:{from_}"
        client.messages.create(body=body, from_=from_, to=to)
        return True
    except Exception:
        logger.exception("Failed to send WhatsApp to %s", to_number)
        return False


def _send_whatsapp_async(to_number: str, body: str) -> None:
    thread = threading.Thread(
        target=_send_whatsapp,
        args=(to_number, body),
        daemon=True,
        name="dashboard-twilio-outbound",
    )
    thread.start()


def _notify_customer_order_confirmed(order_id: str, wa_id: str) -> None:
    if not wa_id:
        return
    body = (
        f"Tu pedido *{order_id}* fue confirmado por el restaurante. "
        "¡Gracias por tu compra!"
    )
    try:
        from app.services.admin_service import AdminService

        _, _, _, admin_service, _ = _bot_services()
        if isinstance(admin_service, AdminService):
            admin_service.notify_customer_order_confirmed(order_id, wa_id)
            return
    except Exception:
        logger.debug("AdminService notify unavailable; using Twilio fallback.", exc_info=True)
    _send_whatsapp_async(wa_id, body)


def _notify_customer_order_confirmed_with_service(
    order_id: str, wa_id: str, admin_service: Any
) -> None:
    """Prefer resolved AdminService and force reliable send from dashboard."""
    if not wa_id:
        logger.warning("Skipping customer notify for %s: empty wa_id", order_id)
        return
    body = (
        f"Tu pedido *{order_id}* fue confirmado por el restaurante. "
        "¡Gracias por tu compra!"
    )
    try:
        from app.services.admin_service import AdminService

        if isinstance(admin_service, AdminService):
            # Dashboard confirmations run in HTTP requests; send synchronously here
            # to avoid losing daemon-thread delivery on short-lived workers.
            sent = admin_service._send_whatsapp(wa_id, body)
            if sent:
                return
            logger.warning(
                "AdminService sync notify failed for %s (%s). Falling back.",
                order_id,
                wa_id,
            )
    except Exception:
        logger.debug(
            "Resolved AdminService notify unavailable; using fallback notifier.",
            exc_info=True,
        )
    _notify_customer_order_confirmed(order_id, wa_id)


def _sync_local_order_status(order_id: str, status: str) -> None:
    """Keep data/orders_cache.json aligned after dashboard writes (standalone Sheets path)."""
    order_id = order_id.strip().upper()
    status = str(status).strip().lower()
    cache_path = settings.PROJECT_ROOT / "data" / "orders_cache.json"
    if not cache_path.exists():
        return
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(payload, dict):
        return
    orders = payload.get("orders")
    if not isinstance(orders, dict):
        return
    entry = orders.get(order_id)
    if not isinstance(entry, dict):
        return
    entry["status"] = status
    orders[order_id] = entry
    payload["orders"] = orders
    dirty_status = payload.get("dirty_status")
    if isinstance(dirty_status, dict):
        dirty_status.pop(order_id, None)
    try:
        with cache_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except OSError:
        logger.warning("Could not update local orders cache for %s", order_id)


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

    _, _, order_service, _, _ = _bot_services()
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

    _sync_local_order_status(order_id, "confirmed")
    _notify_customer_order_confirmed_with_service(
        order_id, order.get("wa_id", ""), admin_service
    )
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

    _, _, order_service, admin_service, _ = _bot_services()
    order = order_service.get_order(order_id)
    if not order:
        return WriteResult(ok=False, message=f"No encontré el pedido {order_id}.")
    previous_status = str(order.get("status", "")).strip().lower()

    if not order_service.update_order_status(order_id, status):
        return WriteResult(
            ok=False,
            message=f"No pude actualizar el pedido {order_id}.",
            entity_id=order_id,
        )
    _sync_local_order_status(order_id, status)
    if status == "confirmed" and previous_status != "confirmed":
        _notify_customer_order_confirmed_with_service(
            order_id, order.get("wa_id", ""), admin_service
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
