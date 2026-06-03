"""Fixed regression checklist (optimization plan — Paso 2).

Run after every optimization step:
    python scripts/regression_checklist.py

Automated:
    - parser validation (25/25)
    - GET /health
    - POST /bot hola  -> 2 Twilio messages
    - POST /bot menu  -> menu loaded (Google Sheets when connected)
    - POST /bot pedido corto -> order review / confirmation prompt

Manual (when using real WhatsApp):
    - Repeat hola, menu, and a short order on the phone and compare behavior.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("TWILIO_REST_WEBHOOK_REPLIES", "0")

from app.app import create_app  # noqa: E402


def _twilio_messages(xml: str) -> list[str]:
    return re.findall(r"<Message>(.*?)</Message>", xml, flags=re.DOTALL)


def check_parser() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "app.core.parser"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    ok = result.returncode == 0 and "PARSER VALIDATION: OK (25/25)" in output
    print(f"[{'OK' if ok else 'FAIL'}] python -m app.core.parser -> 25/25")
    if not ok:
        print(output.strip())
    return ok


def check_health(client) -> bool:
    response = client.get("/health")
    payload = response.get_json(silent=True) or {}
    caches = payload.get("caches") or {}
    ok = (
        response.status_code == 200
        and payload.get("status") == "ok"
        and caches.get("ready") is True
    )
    print(f"[{'OK' if ok else 'FAIL'}] GET /health -> 200 status=ok caches.ready")
    return ok


def check_hola_two_messages(client, wa_id: str) -> bool:
    response = client.post(
        "/bot",
        data={"WaId": wa_id, "ProfileName": "Regression", "Body": "hola"},
    )
    messages = _twilio_messages(response.get_data(as_text=True))
    ok = response.status_code == 200 and len(messages) == 2
    print(f"[{'OK' if ok else 'FAIL'}] WhatsApp hola -> 2 messages (got {len(messages)})")
    return ok


def check_menu_from_sheets(client, wa_id: str, sheets) -> bool:
    menu_items = sheets.get_menu()
    response = client.post(
        "/bot",
        data={"WaId": wa_id, "ProfileName": "Regression", "Body": "menu"},
    )
    body = response.get_data(as_text=True)
    messages = _twilio_messages(body)
    menu_text = messages[0] if messages else body
    has_header = "Nuestro men" in menu_text or "menú" in menu_text.lower()
    has_products = any(
        item.get("nombre", "") in menu_text for item in menu_items[:5]
    )
    ok = (
        response.status_code == 200
        and has_header
        and has_products
        and (not sheets._connected or len(menu_items) > 0)
    )
    source = "Google Sheets" if sheets._connected else "demo fallback"
    print(
        f"[{'OK' if ok else 'FAIL'}] WhatsApp menu -> menu from {source} "
        f"({len(menu_items)} items)"
    )
    return ok


def check_short_order_confirmation(client, wa_id: str) -> bool:
    client.post(
        "/bot",
        data={"WaId": wa_id, "ProfileName": "Regression", "Body": "inicio"},
    )
    client.post(
        "/bot",
        data={"WaId": wa_id, "ProfileName": "Regression", "Body": "pedido"},
    )
    response = client.post(
        "/bot",
        data={"WaId": wa_id, "ProfileName": "Regression", "Body": "1 hamburguesa"},
    )
    messages = _twilio_messages(response.get_data(as_text=True))
    text = messages[0] if messages else response.get_data(as_text=True)
    ok = response.status_code == 200 and "Confirmamos tu pedido" in text
    print(f"[{'OK' if ok else 'FAIL'}] WhatsApp pedido corto -> confirmation prompt")
    return ok


def main() -> int:
    print("=== Regression checklist (Paso 2) ===\n")
    results = [check_parser()]

    app = create_app()
    sheets = app.config["user_service"].sheets
    wa_id = f"regression_{uuid.uuid4().hex[:8]}"
    with app.test_client() as client:
        results.extend(
            [
                check_health(client),
                check_hola_two_messages(client, wa_id),
                check_menu_from_sheets(client, wa_id, sheets),
                check_short_order_confirmation(client, wa_id),
            ]
        )

    passed = sum(results)
    total = len(results)
    print(f"\n=== Result: {passed}/{total} passed ===")
    if passed == total:
        print("Checklist OK. Safe to continue to the next optimization step.")
        return 0

    print("Checklist FAILED. Fix regressions before continuing.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
