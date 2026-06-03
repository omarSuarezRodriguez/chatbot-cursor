"""Verify admin block/unblock commands and blocked-user silence.

Usage:
    python scripts/verify_blocked_users.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("TWILIO_REST_WEBHOOK_REPLIES", "0")

from app.app import create_app  # noqa: E402
from app.config import ADMIN_WHATSAPP_NUMBER  # noqa: E402
from app.services.admin_service import AdminService  # noqa: E402
from app.utils.validators import parse_admin_block_command  # noqa: E402


def main() -> int:
    app = create_app()
    client = app.test_client()
    admin = app.config["admin_service"]
    blocked_cache = app.config["blocked_cache"]
    sheets = admin.sheets

    print("ADMIN_WHATSAPP_NUMBER:", ADMIN_WHATSAPP_NUMBER)

    cases = [
        ("blockoff:+573001234567", ("unblock", "+573001234567")),
        ("blockon:+573009998877", ("block", "+573009998877")),
        ("BLOCKON:573001111111", ("block", "573001111111")),
        ("hola", None),
    ]
    for text, expected in cases:
        got = parse_admin_block_command(text)
        if got != expected:
            print(f"FAIL parse_admin_block_command({text!r}): {got!r} != {expected!r}")
            return 1
    print("OK parse_admin_block_command")

    target = "573009887766"
    admin_wa = "3001111032"
    if not AdminService.is_admin(admin_wa):
        print("FAIL: admin WaId not recognized")
        return 1

    with patch.object(admin, "_send_whatsapp", return_value=True):
        reply = client.post(
            "/bot",
            data={"WaId": admin_wa, "Body": f"blockon:+{target}"},
        ).get_data(as_text=True)

    if "bloqueado correctamente" not in reply.lower():
        print("FAIL: admin block reply:", reply[:300])
        return 1
    if not blocked_cache.is_blocked(target):
        print("FAIL: blocked_cache does not contain target after blockon")
        return 1
    user = sheets.get_user(AdminService._resolve_e164_digits(target))
    if not user.get("blocked"):
        print("FAIL: sheets user not marked blocked:", user)
        return 1
    print(f"OK blockon blocked {target}")

    with patch.object(admin, "_send_whatsapp", return_value=True):
        silent = client.post(
            "/bot",
            data={"WaId": target, "ProfileName": "Blocked", "Body": "hola"},
        ).get_data(as_text=True)

    if "<Message>" in silent or "<Body>" in silent:
        print("FAIL: blocked user received a reply:", silent[:200])
        return 1
    print("OK blocked user receives no reply")

    with patch.object(admin, "_send_whatsapp", return_value=True):
        reply = client.post(
            "/bot",
            data={"WaId": admin_wa, "Body": f"blockoff:+{target}"},
        ).get_data(as_text=True)

    if "desbloqueado correctamente" not in reply.lower():
        print("FAIL: admin unblock reply:", reply[:300])
        return 1
    if blocked_cache.is_blocked(target):
        print("FAIL: blocked_cache still contains target after blockoff")
        return 1
    print(f"OK blockoff unblocked {target}")

    with patch.object(admin, "_send_whatsapp", return_value=True):
        active = client.post(
            "/bot",
            data={"WaId": target, "ProfileName": "Unblocked", "Body": "hola"},
        ).get_data(as_text=True)

    if "<Message>" not in active and "<Body>" not in active:
        print("FAIL: unblocked user got no reply:", active[:200])
        return 1
    print("OK unblocked user receives reply again")

    non_admin = client.post(
        "/bot",
        data={"WaId": "573009999999", "Body": "blockon:+573001234567"},
    ).get_data(as_text=True)
    if "bloqueado" in non_admin.lower() and "573001234567" in non_admin:
        print("FAIL: non-admin executed block command")
        return 1
    print("OK non-admin cannot run block commands")

    print("=== verify_blocked_users: ALL PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
