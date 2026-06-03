"""Verify admin notify + confirm + customer message (local test client).

Usage:
    python scripts/verify_admin_flow.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("TWILIO_REST_WEBHOOK_REPLIES", "0")

from app.app import create_app  # noqa: E402
from app.config import ADMIN_WHATSAPP_NUMBER  # noqa: E402
from app.services.admin_service import AdminService  # noqa: E402


def main() -> int:
    app = create_app()
    client = app.test_client()
    admin = app.config["admin_service"]

    print("ADMIN_WHATSAPP_NUMBER:", ADMIN_WHATSAPP_NUMBER)
    for sample in ("573001111032", "3001111032", "whatsapp:+573001111032"):
        print(f"  is_admin({sample!r}) -> {AdminService.is_admin(sample)}")

    wa_customer = "573009998877"
    order_id = None
    steps = ["pedido", "2 hamburguesa doble carne", "si", "2"]
    outbound: list[tuple[str, str]] = []

    def capture_send(to: str, body: str) -> bool:
        outbound.append((to, body))
        return True

    with patch.object(admin, "_send_whatsapp", side_effect=capture_send):
        for body in steps:
            response = client.post(
                "/bot",
                data={"WaId": wa_customer, "ProfileName": "Test", "Body": body},
            )
            text = response.get_data(as_text=True)
            match = re.search(r"ORD-[A-F0-9]{8}", text)
            if match:
                order_id = match.group(0)
                break

    if not order_id:
        print("FAIL: no order created")
        return 1

    admin_msgs = [m for m in outbound if "Nuevo pedido" in m[1]]
    print(f"OK order {order_id} created; admin alerts: {len(admin_msgs)}")
    if not admin_msgs:
        print("FAIL: admin was not notified on save")
        return 1

    outbound.clear()
    admin_wa = "3001111032"
    with patch.object(admin, "_send_whatsapp", side_effect=capture_send):
        response = client.post(
            "/bot",
            data={"WaId": admin_wa, "Body": f"CONFIRMAR {order_id}"},
        )
        reply = response.get_data(as_text=True)

    if not AdminService.is_admin(admin_wa):
        print("FAIL: admin WaId without country code not recognized")
        return 1
    if "confirmado correctamente" not in reply.lower():
        print("FAIL: admin confirm reply:", reply[:200])
        return 1

    customer_msgs = [m for m in outbound if "fue confirmado" in m[1]]
    if len(customer_msgs) != 1:
        print("FAIL: customer confirm messages:", outbound)
        return 1

    to_addr = admin._format_whatsapp_address(wa_customer)
    sent_to = admin._format_whatsapp_address(customer_msgs[0][0])
    if sent_to != to_addr:
        print(f"FAIL: customer sent to {customer_msgs[0][0]!r} ({sent_to!r}), expected {to_addr!r}")
        return 1

    print(f"OK admin confirm via WaId {admin_wa}")
    print(f"OK customer notified at {to_addr}")

    # Regression: WaId de 11 dígitos (común en pedidos reales sin prefijo 57)
    outbound.clear()
    order_id2 = None
    wa_11 = "35699155990"
    with patch.object(admin, "_send_whatsapp", side_effect=capture_send):
        for body in ["pedido", "1 hamburguesa doble carne", "si", "2"]:
            response = client.post(
                "/bot",
                data={"WaId": wa_11, "ProfileName": "Cliente11", "Body": body},
            )
            match = re.search(r"ORD-[A-F0-9]{8}", response.get_data(as_text=True))
            if match:
                order_id2 = match.group(0)
        if not order_id2:
            print("FAIL: no order for 11-digit wa_id test")
            return 1
        client.post(
            "/bot",
            data={"WaId": admin_wa, "Body": f"CONFIRMAR {order_id2}"},
        )
    expected_11 = "whatsapp:+35699155990"
    confirm_msgs = [m for m in outbound if "fue confirmado" in m[1]]
    if len(confirm_msgs) != 1:
        print("FAIL: 11-digit customer confirm messages:", outbound)
        return 1
    sent_11 = admin._format_whatsapp_address(confirm_msgs[0][0])
    if sent_11 != expected_11:
        print(f"FAIL: 11-digit wa_id sent to {sent_11!r}, expected {expected_11!r}")
        return 1
    print(f"OK 11-digit customer target {expected_11}")

    # From de Twilio prevalece (cada cliente con su E.164 real)
    outbound.clear()
    with patch.object(admin, "_send_whatsapp", side_effect=capture_send):
        client.post(
            "/bot",
            data={
                "WaId": "3009988877",
                "From": "whatsapp:+573009998877",
                "Body": "hola",
            },
        )
    if outbound:
        sent = admin._format_whatsapp_address(outbound[-1][0])
        if sent != "whatsapp:+573009998877":
            print(f"FAIL: From E.164 expected +573009998877, got {sent!r}")
            return 1
    print("OK Twilio From used for outbound (+573009998877)")

    cases = [
        ("573009998877", "573009998877"),
        ("3001111032", "573001111032"),
        ("35699155990", "35699155990"),
        ("3569915590", "3569915590"),
        ("whatsapp:+573569915590", "3569915590"),
        ("14155552671", "14155552671"),
    ]
    for raw, expected in cases:
        got = AdminService._resolve_e164_digits(raw)
        if got != expected:
            print(f"FAIL resolve {raw!r}: got {got!r}, expected {expected!r}")
            return 1
    print("OK generic resolve cases")

    prod = AdminService.canonical_wa_id(
        "35699155990", "whatsapp:+3569915590"
    )
    prod_fmt = admin._format_whatsapp_address(prod)
    if prod != "35699155990" or prod_fmt != "whatsapp:+35699155990":
        print(f"FAIL: Malta canonical {prod!r} -> {prod_fmt!r}")
        return 1
    print("OK Malta WaId/From -> whatsapp:+35699155990")

    print("=== verify_admin_flow: ALL PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
