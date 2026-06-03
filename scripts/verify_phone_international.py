"""Pruebas E.164 multi-país (Colombia, Malta, EE.UU., Europa, LATAM, etc.).

Usage:
    python scripts/verify_phone_international.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.app import create_app  # noqa: E402
from app.services.admin_service import AdminService  # noqa: E402

# (entrada, dígitos E.164 esperados, país)
CASES = [
    ("573009998877", "573009998877", "Colombia E.164"),
    ("3001111032", "573001111032", "Colombia nacional"),
    ("35699155990", "35699155990", "Malta"),
    ("3569915590", "3569915590", "Malta corto"),
    ("whatsapp:+573569915590", "3569915590", "Malta legacy con 57 erróneo"),
    ("14155552671", "14155552671", "EE.UU."),
    ("12025550123", "12025550123", "EE.UU. Washington"),
    ("34612345678", "34612345678", "España"),
    ("447911123456", "447911123456", "Reino Unido"),
    ("491701234567", "491701234567", "Alemania"),
    ("33612345678", "33612345678", "Francia"),
    ("393331234567", "393331234567", "Italia"),
    ("525512345678", "525512345678", "México"),
    ("5511987654321", "5511987654321", "Brasil"),
    ("5491123456789", "5491123456789", "Argentina"),
    ("51987654321", "51987654321", "Perú"),
    ("56912345678", "56912345678", "Chile"),
    ("351912345678", "351912345678", "Portugal"),
    ("41791234567", "41791234567", "Suiza"),
    ("31612345678", "31612345678", "Países Bajos"),
    ("61234567890", "61234567890", "Australia"),
    ("819012345678", "819012345678", "Japón"),
    ("8613800138000", "8613800138000", "China"),
    ("971501234567", "971501234567", "EAU"),
]


def test_resolve() -> bool:
    ok = True
    for raw, expected, label in CASES:
        got = AdminService._resolve_e164_digits(raw)
        addr = f"whatsapp:+{got}" if got else raw
        if got != expected:
            print(f"FAIL [{label}] {raw!r} -> {got!r}, expected {expected!r}")
            ok = False
        else:
            print(f"OK [{label}] -> {addr}")
    return ok


def test_canonical_international() -> bool:
    ok = True
    pairs = [
        ("35699155990", "whatsapp:+573569915590", "35699155990", "Malta vs From CO erróneo"),
        ("34612345678", "whatsapp:+34612345678", "34612345678", "España From"),
        ("3009988877", "whatsapp:+573009998877", "573009998877", "Colombia From completo"),
    ]
    for wa_id, from_n, expected, label in pairs:
        got = AdminService.canonical_wa_id(wa_id, from_n)
        if got != expected:
            print(f"FAIL canonical [{label}]: {got!r} != {expected!r}")
            ok = False
        else:
            print(f"OK canonical [{label}] -> +{got}")
    return ok


def test_webhook_outbound() -> bool:
    app = create_app()
    client = app.test_client()
    admin = app.config["admin_service"]
    scenarios = [
        (
            {"WaId": "14155552671", "From": "whatsapp:+14155552671", "Body": "Hi"},
            "whatsapp:+14155552671",
            "EE.UU.",
        ),
        (
            {"WaId": "34612345678", "From": "whatsapp:+34612345678", "Body": "Hola"},
            "whatsapp:+34612345678",
            "España",
        ),
        (
            {"WaId": "35699155990", "From": "whatsapp:+3569915590", "Body": "Hola"},
            "whatsapp:+35699155990",
            "Malta",
        ),
        (
            {"WaId": "3001111032", "From": "whatsapp:+573001111032", "Body": "Hola"},
            "whatsapp:+573001111032",
            "Colombia",
        ),
    ]
    ok = True
    for data, expected, label in scenarios:
        captured: list[str] = []

        def capture(to: str, body: str) -> bool:
            captured.append(admin._format_whatsapp_address(to))
            return True

        with patch.object(admin, "_send_whatsapp", side_effect=capture):
            client.post("/bot", data=data)
        if not captured:
            print(f"SKIP webhook [{label}] (TwiML)")
            continue
        if captured[-1] != expected:
            print(f"FAIL webhook [{label}]: {captured[-1]!r} != {expected!r}")
            ok = False
        else:
            print(f"OK webhook [{label}] -> {expected}")
    return ok


def test_valid_e164() -> bool:
    ok = True
    for digits, label in [
        ("573009998877", "CO"),
        ("35699155990", "Malta"),
        ("14155552671", "US"),
        ("34612345678", "ES"),
    ]:
        if not AdminService._e164_digits_valid(digits):
            print(f"FAIL valid [{label}] {digits}")
            ok = False
    if ok:
        print("OK _e164_digits_valid multi-país")
    return ok


def main() -> int:
    steps = [
        ("resolve", test_resolve),
        ("canonical", test_canonical_international),
        ("valid", test_valid_e164),
        ("webhook", test_webhook_outbound),
    ]
    for name, fn in steps:
        print(f"\n--- {name} ---")
        if not fn():
            print(f"\n=== verify_phone_international: FAILED ({name}) ===")
            return 1
    print("\n=== verify_phone_international: ALL PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
