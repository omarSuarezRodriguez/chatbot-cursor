"""Admin notifications, confirmations and reminder scheduler."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import (
    ADMIN_REMINDER_INTERVAL_SECONDS,
    ADMIN_REMINDER_MAX_SECONDS,
    ADMIN_WHATSAPP_NUMBER,
    PARSER_ERROR_LOG_PATH,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
)
from app.core.parser import OrderParser
from app.integrations.google_sheets import GoogleSheetsClient
from app.services.order_service import OrderService
from app.utils.validators import extract_admin_order_id, is_admin_confirm

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, sheets: GoogleSheetsClient, order_service: OrderService) -> None:
        self.sheets = sheets
        self.order_service = order_service
        self._reminder_state: Dict[str, Dict[str, Any]] = {}
        self._scheduler_started = False
        self._lock = threading.Lock()

    @staticmethod
    def _normalize_phone(value: str) -> str:
        return "".join(
            ch for ch in value.replace("whatsapp:", "").strip() if ch.isdigit()
        )

    @staticmethod
    def is_admin(wa_id: str) -> bool:
        if not ADMIN_WHATSAPP_NUMBER:
            return False
        normalized_admin = AdminService._normalize_phone(ADMIN_WHATSAPP_NUMBER)
        normalized_wa = AdminService._normalize_phone(wa_id)
        return bool(normalized_admin) and normalized_wa == normalized_admin

    def _format_whatsapp_address(self, number: str) -> str:
        stripped = number.replace("whatsapp:", "").strip()
        digits = "".join(ch for ch in stripped if ch.isdigit())
        if digits and not stripped.startswith("+"):
            stripped = f"+{digits}"
        prefix = "whatsapp:" if not number.startswith("whatsapp:") else ""
        return f"{prefix}{stripped}" if prefix else stripped

    def _send_whatsapp(self, to_number: str, body: str) -> bool:
        if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
            logger.info("Twilio outbound not configured. Admin message: %s", body[:120])
            return False
        try:
            from twilio.rest import Client

            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            to = self._format_whatsapp_address(to_number)
            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"
            from_ = self._format_whatsapp_address(TWILIO_WHATSAPP_FROM)
            if not from_.startswith("whatsapp:"):
                from_ = f"whatsapp:{from_}"
            client.messages.create(body=body, from_=from_, to=to)
            return True
        except Exception:
            logger.exception("Failed to send WhatsApp to %s", to_number)
            return False

    def _send_whatsapp_async(self, to_number: str, body: str) -> None:
        thread = threading.Thread(
            target=self._send_whatsapp,
            args=(to_number, body),
            daemon=True,
            name="twilio-outbound",
        )
        thread.start()

    def notify_customer_order_confirmed(self, order_id: str, wa_id: str) -> None:
        if not wa_id:
            return
        self._send_whatsapp_async(
            wa_id,
            f"Tu pedido *{order_id}* fue confirmado por el restaurante. "
            "¡Gracias por tu compra!",
        )

    def notify_new_order(self, order: Dict[str, Any]) -> None:
        if not ADMIN_WHATSAPP_NUMBER:
            logger.warning("ADMIN_WHATSAPP_NUMBER not set; skipping admin notification.")
            return

        items = order.get("items", [])
        lines = OrderParser.format_cart(items).split("\n") if items else ["(vacío)"]
        message = (
            f"*Nuevo pedido {order.get('order_id')}*\n"
            f"Cliente: {order.get('customer_name') or 'Sin nombre'}\n"
            f"Teléfono: {order.get('wa_id')}\n"
            f"Dirección: {order.get('address') or 'N/A'}\n"
            f"Entrega: {order.get('delivery_type') or 'N/A'}\n\n"
            f"{chr(10).join(lines)}\n\n"
            f"Responde *CONFIRMAR {order.get('order_id')}* o *pedido {order.get('order_id')} listo* para aceptar el pedido."
        )
        self._send_whatsapp_async(ADMIN_WHATSAPP_NUMBER, message)
        self._track_pending_reminder(order.get("order_id", ""))

    def handle_admin_message(self, body: str) -> str:
        if not is_admin_confirm(body):
            return (
                "Comando admin no reconocido.\n"
                "Responde: *CONFIRMAR ORD-XXXXXXXX* o *pedido ORD-XXXXXXXX listo*"
            )

        order_id = extract_admin_order_id(body)
        if not order_id:
            return "Indica el ID del pedido. Ejemplo: *CONFIRMAR ORD-A1B2C3D4*"

        order = self.order_service.get_order(order_id)
        if not order:
            return f"No encontré el pedido *{order_id}*."

        if order.get("status") == "confirmed":
            self._clear_reminder(order_id)
            return (
                f"El pedido *{order_id}* ya fue confirmado. "
                "No recibirás más recordatorios sobre él."
            )

        if self.order_service.confirm_order(order_id):
            self._clear_reminder(order_id)
            self.notify_customer_order_confirmed(order_id, order.get("wa_id", ""))
            return f"Pedido *{order_id}* confirmado correctamente."

        return f"No pude actualizar el pedido *{order_id}*."

    def _track_pending_reminder(self, order_id: str) -> None:
        if not order_id:
            return
        with self._lock:
            self._reminder_state[order_id] = {
                "started_at": time.time(),
                "last_sent": time.time(),
            }

    def _clear_reminder(self, order_id: str) -> None:
        with self._lock:
            self._reminder_state.pop(order_id, None)

    def start_reminder_scheduler(self) -> None:
        if self._scheduler_started or not ADMIN_WHATSAPP_NUMBER:
            return
        self._scheduler_started = True
        thread = threading.Thread(target=self._reminder_loop, daemon=True)
        thread.start()
        logger.info("Admin reminder scheduler started.")

    def _reminder_loop(self) -> None:
        while True:
            try:
                self._process_reminders()
            except Exception:
                logger.exception("Admin reminder loop error (non-fatal)")
            time.sleep(ADMIN_REMINDER_INTERVAL_SECONDS)

    def _process_reminders(self) -> None:
        now = time.time()
        pending_orders = self.sheets.get_pending_orders()
        pending_ids = {order.get("order_id") for order in pending_orders}

        with self._lock:
            tracked = dict(self._reminder_state)

        for order_id, state in tracked.items():
            if order_id not in pending_ids:
                self._clear_reminder(order_id)
                continue

            elapsed = now - float(state.get("started_at", now))
            since_last = now - float(state.get("last_sent", now))
            if elapsed >= ADMIN_REMINDER_MAX_SECONDS:
                self._log_reminder_stopped(order_id, elapsed)
                self._clear_reminder(order_id)
                continue
            if since_last < ADMIN_REMINDER_INTERVAL_SECONDS:
                continue

            self._send_whatsapp(
                ADMIN_WHATSAPP_NUMBER,
                f"Recordatorio: pedido *{order_id}* sigue pendiente. "
                f"Responde *CONFIRMAR {order_id}* o *pedido {order_id} listo*.",
            )
            with self._lock:
                if order_id in self._reminder_state:
                    self._reminder_state[order_id]["last_sent"] = now

    @staticmethod
    def _log_reminder_stopped(order_id: str, elapsed: float) -> None:
        try:
            from pathlib import Path
            import json

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "admin_reminder_stopped",
                "order_id": order_id,
                "elapsed_seconds": int(elapsed),
            }
            path = Path(PARSER_ERROR_LOG_PATH)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Failed to log reminder stop event")
