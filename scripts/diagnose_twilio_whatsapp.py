"""Diagnose Twilio WhatsApp delivery for admin alerts.

Usage:
    python scripts/diagnose_twilio_whatsapp.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import (  # noqa: E402
    ADMIN_WHATSAPP_NUMBER,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    TWILIO_WHATSAPP_SANDBOX_NUMBER,
    is_twilio_whatsapp_sandbox,
)
from app.integrations.google_sheets import get_google_sheets_client  # noqa: E402
from app.services.admin_service import AdminService  # noqa: E402
from app.services.menu_service import MenuService  # noqa: E402
from app.services.order_service import OrderService  # noqa: E402


def main() -> int:
    print("=== Diagnóstico Twilio WhatsApp (admin) ===\n")

    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM]):
        print("FAIL: Faltan TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN o TWILIO_WHATSAPP_FROM en .env")
        return 1

    if not ADMIN_WHATSAPP_NUMBER:
        print("FAIL: Falta ADMIN_WHATSAPP_NUMBER en .env")
        return 1

    print(f"FROM (bot):  {TWILIO_WHATSAPP_FROM}")
    print(f"ADMIN:       {ADMIN_WHATSAPP_NUMBER}")
    print(f"Sandbox:     {is_twilio_whatsapp_sandbox()}")

    try:
        from twilio.rest import Client

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        print(f"Cuenta Twilio: status={account.status!r} type={getattr(account, 'type', '?')!r}")
        if getattr(account, "type", "") == "Trial":
            print(
                "\nAVISO: La cuenta sigue en modo TRIAL (limite ~50 msgs/dia)."
                "\n   Pagar saldo NO basta: en Console -> Account -> Upgrade account."
            )
    except Exception as exc:
        print(f"No se pudo leer la cuenta Twilio: {exc}")

    if is_twilio_whatsapp_sandbox():
        print(
            f"\nAVISO: Usas el numero SANDBOX {TWILIO_WHATSAPP_SANDBOX_NUMBER}."
            "\n   Para restaurante en produccion registra tu numero WhatsApp Business"
            "\n   en Twilio y cambia TWILIO_WHATSAPP_FROM en .env."
            "\n   El admin debe enviar join <codigo> a ese sandbox si sigues en pruebas."
        )

    import os

    sheets = get_google_sheets_client(
        os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", ""),
        os.getenv("GOOGLE_SPREADSHEET_ID", ""),
    )
    admin = AdminService(sheets, OrderService(sheets, MenuService(sheets)))

    print("\nEnviando mensaje de prueba al admin...")
    ok = admin._send_whatsapp(
        ADMIN_WHATSAPP_NUMBER,
        "Diagnostico bot restaurante — si lees esto, Twilio entrega OK.",
    )

    if ok:
        print("\nOK: Twilio aceptó y el mensaje NO está en failed/undelivered.")
        print("Revise WhatsApp del admin en los próximos segundos.")
        return 0

    print("\nFAIL: El mensaje no se entregó. Revise los ERROR en consola arriba.")
    print("Ejecute también: python scripts/verify_admin_flow.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
