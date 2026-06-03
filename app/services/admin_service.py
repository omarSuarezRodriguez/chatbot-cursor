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
    TWILIO_WHATSAPP_SANDBOX_NUMBER,
    is_twilio_whatsapp_sandbox,
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
        self._last_twilio_error_code: Optional[int] = None

    @property
    def last_twilio_error_code(self) -> Optional[int]:
        return self._last_twilio_error_code

    @staticmethod
    def _normalize_phone(value: str) -> str:
        return "".join(
            ch for ch in value.replace("whatsapp:", "").strip() if ch.isdigit()
        )

    @classmethod
    def _default_country_prefix(cls) -> str:
        admin_digits = cls._normalize_phone(ADMIN_WHATSAPP_NUMBER)
        if len(admin_digits) > 10:
            return admin_digits[: len(admin_digits) - 10]
        return "57"

    @classmethod
    def _dedupe_country_prefix(cls, digits: str, prefix: str) -> str:
        if not prefix:
            return digits
        doubled = prefix + prefix
        while digits.startswith(doubled):
            digits = digits[len(prefix) :]
        return digits

    @classmethod
    def _resolve_e164_digits(cls, number: str) -> str:
        digits = cls._normalize_phone(number)
        if not digits:
            return ""
        prefix = cls._default_country_prefix()
        digits = cls._dedupe_country_prefix(digits, prefix)
        if len(digits) >= 12 and digits.startswith(prefix):
            return digits
        if len(digits) == 10 and digits.startswith("3"):
            return f"{prefix}{digits}"
        # WaId sin 57 (11 dígitos): suele ser 10 nacionales + dígito extra al final
        if len(digits) == 11 and digits.startswith("3") and prefix == "57":
            national = digits[:9] + digits[-1]
            if len(national) == 10 and national.startswith("3"):
                return f"{prefix}{national}"
            for i in range(len(digits)):
                candidate = digits[:i] + digits[i + 1 :]
                if len(candidate) == 10 and candidate.startswith("3"):
                    return f"{prefix}{candidate}"
            return f"{prefix}{digits[-10:]}"
        return digits

    def _customer_wa_id(self, order: Dict[str, Any]) -> str:
        raw = str(order.get("wa_id", "")).strip()
        return self._resolve_e164_digits(raw) or raw

    @staticmethod
    def _phones_match(a: str, b: str) -> bool:
        normalized_a = AdminService._normalize_phone(a)
        normalized_b = AdminService._normalize_phone(b)
        if not normalized_a or not normalized_b:
            return False
        if normalized_a == normalized_b:
            return True
        # Twilio WaId may omit country code (e.g. 3001111032 vs 573001111032).
        if len(normalized_a) >= 10 and len(normalized_b) >= 10:
            return normalized_a[-10:] == normalized_b[-10:]
        return False

    @staticmethod
    def is_bot_number(wa_id: str) -> bool:
        """True if wa_id is the outbound bot line (TWILIO_WHATSAPP_FROM)."""
        if not TWILIO_WHATSAPP_FROM or not wa_id:
            return False
        return AdminService._phones_match(wa_id, TWILIO_WHATSAPP_FROM)

    @staticmethod
    def is_admin(wa_id: str) -> bool:
        if not ADMIN_WHATSAPP_NUMBER or not wa_id:
            return False
        # The bot line is always customer-facing, never admin commands.
        if AdminService.is_bot_number(wa_id):
            return False
        return AdminService._phones_match(wa_id, ADMIN_WHATSAPP_NUMBER)

    def _format_whatsapp_address(self, number: str) -> str:
        digits = self._resolve_e164_digits(number)
        if not digits:
            return number.strip()
        return f"whatsapp:+{digits}"

    @classmethod
    def _e164_digits_valid(cls, digits: str) -> bool:
        if not digits or not digits.isdigit():
            return False
        prefix = cls._default_country_prefix()
        if prefix == "57":
            return len(digits) == 12 and digits.startswith("57")
        return 10 <= len(digits) <= 15

    @staticmethod
    def _twilio_error_hint(code: Optional[int]) -> str:
        hints = {
            63015: (
                "El admin no ha unido el sandbox. Desde WhatsApp envíe join <código> "
                f"al {TWILIO_WHATSAPP_SANDBOX_NUMBER}."
            ),
            63038: (
                "Límite diario de la cuenta agotado (ventana 24 h; Twilio puede "
                "mostrar 50 aunque la cuenta sea Full). Espere el reinicio, revise "
                "Messaging Insights o contacte soporte Twilio para subir el cupo."
            ),
            63016: "Fuera de ventana 24 h: hace falta plantilla WhatsApp aprobada.",
            63024: (
                "Destinatario inválido para WhatsApp. Use E.164 en .env "
                "(ej. whatsapp:+573001234567), sin repetir el prefijo 57, "
                "y confirme que el número tenga WhatsApp activo."
            ),
            63112: "Meta bloqueó el mensaje. Verifique el número WhatsApp Business.",
        }
        return hints.get(code, "Ver Twilio Console → Monitor → Logs.")

    def _send_whatsapp(self, to_number: str, body: str) -> bool:
        self._last_twilio_error_code = None
        if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
            logger.info("Twilio outbound not configured. Admin message: %s", body[:120])
            return False
        if is_twilio_whatsapp_sandbox():
            logger.warning(
                "TWILIO_WHATSAPP_FROM es el sandbox %s. Para producción use su número "
                "WhatsApp Business registrado en Twilio.",
                TWILIO_WHATSAPP_SANDBOX_NUMBER,
            )
        to_digits = self._resolve_e164_digits(to_number)
        if not self._e164_digits_valid(to_digits):
            logger.error(
                "WhatsApp destino inválido (E.164): raw=%r normalizado=%r. "
                "Revise ADMIN_WHATSAPP_NUMBER o el wa_id del cliente en .env.",
                to_number,
                to_digits or "(vacío)",
            )
            return False
        try:
            from twilio.rest import Client

            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            to = f"whatsapp:+{to_digits}"
            from_ = self._format_whatsapp_address(TWILIO_WHATSAPP_FROM)
            message = client.messages.create(body=body, from_=from_, to=to)
            # Twilio may accept the API call but mark the message failed afterward.
            if message.sid:
                message = client.messages(message.sid).fetch()
            status = getattr(message, "status", "") or ""
            error_code = getattr(message, "error_code", None)
            if status in {"failed", "undelivered"} or error_code:
                code_int = int(error_code) if error_code else None
                self._last_twilio_error_code = code_int
                hint = self._twilio_error_hint(code_int)
                logger.error(
                    "WhatsApp NO entregado a %s (status=%s, code=%s). %s",
                    to,
                    status,
                    error_code,
                    hint,
                )
                return False
            logger.info(
                "WhatsApp entregado a %s (sid=%s, status=%s)",
                to,
                message.sid,
                status,
            )
            return True
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code:
                self._last_twilio_error_code = int(code)
            hint = self._twilio_error_hint(int(code) if code else None)
            logger.error(
                "Failed to send WhatsApp to %s (code=%s): %s. %s",
                to_number,
                code,
                exc,
                hint,
            )
            return False

    def _send_whatsapp_async(self, to_number: str, body: str) -> None:
        thread = threading.Thread(
            target=self._send_whatsapp,
            args=(to_number, body),
            daemon=True,
            name="twilio-outbound",
        )
        thread.start()

    @staticmethod
    def _format_order_lines(items: List[Dict[str, Any]]) -> List[str]:
        if not items:
            return ["(vacío)"]
        lines: List[str] = []
        for item in items:
            name = (
                item.get("product")
                or item.get("nombre")
                or item.get("name")
                or "Producto"
            )
            qty = item.get("qty", item.get("quantity", 1))
            try:
                qty = int(qty)
            except (TypeError, ValueError):
                qty = 1
            subtotal = item.get("subtotal")
            if subtotal is None:
                unit = float(item.get("unit_price") or item.get("precio") or 0)
                subtotal = round(qty * unit, 2)
            else:
                subtotal = float(subtotal)
            lines.append(f"• {qty} x {name} — ${subtotal:.2f}")
        return lines

    def _order_lines_for_admin(self, items: List[Dict[str, Any]]) -> List[str]:
        if not items:
            return ["(vacío)"]
        try:
            formatted = OrderParser.format_cart(items)
            return formatted.split("\n") if formatted else ["(vacío)"]
        except (KeyError, TypeError, ValueError):
            logger.warning(
                "Admin notify: using fallback cart format (%d items)", len(items)
            )
            return self._format_order_lines(items)

    def notify_new_order(self, order: Dict[str, Any]) -> None:
        if not ADMIN_WHATSAPP_NUMBER:
            logger.warning("ADMIN_WHATSAPP_NUMBER not set; skipping admin notification.")
            return

        order_id = order.get("order_id", "")
        items = order.get("items", [])
        lines = self._order_lines_for_admin(items)
        message = (
            f"*Nuevo pedido {order_id}*\n"
            f"Cliente: {order.get('customer_name') or 'Sin nombre'}\n"
            f"Teléfono: {order.get('wa_id')}\n"
            f"Dirección: {order.get('address') or 'N/A'}\n"
            f"Entrega: {order.get('delivery_type') or 'N/A'}\n\n"
            f"{chr(10).join(lines)}\n\n"
            f"Responde *CONFIRMAR {order_id}* o *pedido {order_id} listo* "
            "para aceptar el pedido."
        )
        # Synchronous send: daemon threads may not finish before the webhook returns
        # (common on cloud hosting), so the admin would never get the alert.
        if self._send_whatsapp(ADMIN_WHATSAPP_NUMBER, message):
            logger.info("Admin WhatsApp notified for order %s", order_id)
        else:
            logger.error(
                "Admin WhatsApp NOT sent for order %s — revisa el error Twilio arriba "
                "(común: 63038 = límite diario Twilio, ver hint arriba)",
                order_id,
            )
        self._track_pending_reminder(order_id)

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
            customer = self._customer_wa_id(order)
            if not customer:
                return (
                    f"Pedido *{order_id}* confirmado en sistema, "
                    "pero no hay teléfono del cliente para avisarle."
                )
            confirm_body = (
                f"Tu pedido *{order_id}* fue confirmado por el restaurante. "
                "¡Gracias por tu compra!"
            )
            target = self._format_whatsapp_address(customer)
            if self._send_whatsapp(customer, confirm_body):
                logger.info(
                    "Customer notified at %s for confirmed order %s",
                    target,
                    order_id,
                )
                return (
                    f"Pedido *{order_id}* confirmado correctamente.\n"
                    f"Se avisó al cliente en {target}."
                )
            logger.error(
                "Customer NOT notified at %s for order %s (Twilio delivery failed)",
                target,
                order_id,
            )
            return (
                f"Pedido *{order_id}* confirmado en sistema, "
                f"pero NO se pudo enviar WhatsApp al cliente ({target}). "
                "Verifique que el cliente tenga join al sandbox o número válido."
            )

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


if ADMIN_WHATSAPP_NUMBER and TWILIO_WHATSAPP_FROM:
    if AdminService._phones_match(ADMIN_WHATSAPP_NUMBER, TWILIO_WHATSAPP_FROM):
        logger.warning(
            "ADMIN_WHATSAPP_NUMBER y TWILIO_WHATSAPP_FROM apuntan al mismo numero (%s). "
            "TWILIO_WHATSAPP_FROM debe ser el bot de clientes; "
            "ADMIN_WHATSAPP_NUMBER debe ser el celular del administrador.",
            TWILIO_WHATSAPP_FROM,
        )
    admin_e164 = AdminService._resolve_e164_digits(ADMIN_WHATSAPP_NUMBER)
    if admin_e164 and not AdminService._e164_digits_valid(admin_e164):
        logger.warning(
            "ADMIN_WHATSAPP_NUMBER no es E.164 válido para Colombia: raw=%s normalizado=%s. "
            "Use whatsapp:+57XXXXXXXXXX (12 dígitos con prefijo 57, sin duplicar 57).",
            ADMIN_WHATSAPP_NUMBER,
            admin_e164,
        )
