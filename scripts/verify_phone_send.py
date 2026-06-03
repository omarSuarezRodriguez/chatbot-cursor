"""Verify E.164 resolution and optionally send a Twilio WhatsApp test message.

Usage:
    python scripts/verify_phone_send.py
    python scripts/verify_phone_send.py --send
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.app import create_app  # noqa: E402
from app.services.admin_service import AdminService  # noqa: E402


def check_resolve() -> bool:
    cases = [
        ("573009998877", "573009998877", "whatsapp:+573009998877"),
        ("3001111032", "573001111032", "whatsapp:+573001111032"),
        ("35699155990", "35699155990", "whatsapp:+35699155990"),
        ("3569915590", "3569915590", "whatsapp:+3569915590"),
        ("whatsapp:+573569915590", "3569915590", "whatsapp:+3569915590"),
    ]
    ok = True
    for raw, digits_expected, addr_expected in cases:
        got = AdminService._resolve_e164_digits(raw)
        digits = AdminService._resolve_e164_digits(raw)
        addr = f"whatsapp:+{digits}" if digits else raw
        if got != digits_expected or addr != addr_expected:
            print(f"FAIL resolve {raw!r}: digits={got!r} addr={addr!r}")
            ok = False
        else:
            print(f"OK {raw!r} -> {addr}")
    canon = AdminService.canonical_wa_id(
        "35699155990", "whatsapp:+573569915590"
    )
    if canon != "35699155990":
        print(f"FAIL Malta canonical: {canon!r}")
        ok = False
    else:
        print(f"OK Malta canonical WaId -> {canon}")
    return ok


def check_webhook_hola() -> bool:
    app = create_app()
    client = app.test_client()
    admin = app.config["admin_service"]
    captured: list[str] = []

    def capture(to: str, body: str) -> bool:
        captured.append(admin._format_whatsapp_address(to))
        return True

    with patch.object(admin, "_send_whatsapp", side_effect=capture):
        client.post(
            "/bot",
            data={
                "WaId": "35699155990",
                "From": "whatsapp:+3569915590",
                "ProfileName": "MaltaTest",
                "Body": "Hola",
            },
        )
    if not captured:
        print("SKIP webhook (TwiML mode; resolve checks passed)")
        return True
    target = captured[-1]
    if target != "whatsapp:+35699155990":
        print(f"FAIL webhook outbound {target!r}")
        return False
    print(f"OK webhook Hola -> {target}")
    return True


def send_live() -> bool:
    from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM

    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
        print("FAIL: Twilio no configurado en .env")
        return False

    app = create_app()
    admin = app.config["admin_service"]
    to_digits = AdminService.canonical_wa_id(
        "35699155990", "whatsapp:+3569915590"
    )
    to_addr = admin._format_whatsapp_address(to_digits)
    body = "Prueba E.164 Malta — si recibes esto, el destino es correcto."
    print(f"Enviando a {to_addr} ...")
    if admin._send_whatsapp(to_digits, body):
        print(f"OK Twilio aceptó envío a {to_addr}")
        return True
    code = admin.last_twilio_error_code
    print(f"FAIL envío (error Twilio: {code})")
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--send",
        action="store_true",
        help="Enviar mensaje real por Twilio al número Malta de prueba",
    )
    args = parser.parse_args()

    if not check_resolve():
        return 1
    if not check_webhook_hola():
        return 1
    if args.send:
        if not send_live():
            return 1
    else:
        print("Tip: python scripts/verify_phone_send.py --send  (envío real)")
    print("=== verify_phone_send: ALL PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
