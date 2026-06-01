"""Paso 11 — verify deployed webhook (health + latency).

Usage:
    DEPLOY_URL=https://your-app.onrender.com python scripts/verify_deployment.py

Local (waitress running):
    python scripts/verify_deployment.py
"""

from __future__ import annotations

import os
import re
import sys
import time
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_BASE = "http://127.0.0.1:5000"
BASE = os.getenv("DEPLOY_URL", DEFAULT_BASE).rstrip("/")
TIMEOUT = int(os.getenv("DEPLOY_TIMEOUT", "60"))


def _twilio_messages(xml: str) -> list[str]:
    return re.findall(r"<Message>(.*?)</Message>", xml, flags=re.DOTALL)


def main() -> int:
    print(f"=== Deployment verify (Paso 11) ===\nTarget: {BASE}\n")
    ok = True

    try:
        started = time.perf_counter()
        response = requests.get(f"{BASE}/health", timeout=TIMEOUT)
        health_ms = (time.perf_counter() - started) * 1000
        payload = response.json()
        if response.status_code == 200 and payload.get("status") == "ok":
            caches = payload.get("caches") or {}
            ready = caches.get("ready", False)
            print(
                f"[OK] GET /health -> {health_ms:.0f} ms status=ok "
                f"caches.ready={ready}"
            )
            if not ready:
                ok = False
                print("[FAIL] caches not ready after warm-up")
        else:
            ok = False
            print(f"[FAIL] GET /health -> {response.status_code} {payload}")
    except requests.RequestException as exc:
        ok = False
        print(f"[FAIL] GET /health -> {exc}")
        return 1

    wa_id = f"deploy_{uuid.uuid4().hex[:8]}"
    try:
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/bot",
            data={"WaId": wa_id, "ProfileName": "DeployTest", "Body": "hola"},
            timeout=TIMEOUT,
        )
        hola_ms = (time.perf_counter() - started) * 1000
        messages = _twilio_messages(response.text)
        if response.status_code == 200 and len(messages) == 2:
            print(f"[OK] POST /bot hola -> {hola_ms:.0f} ms ({len(messages)} messages)")
        else:
            ok = False
            print(
                f"[FAIL] POST /bot hola -> {response.status_code}, "
                f"messages={len(messages)}"
            )
    except requests.RequestException as exc:
        ok = False
        print(f"[FAIL] POST /bot hola -> {exc}")

    print()
    if ok:
        print("Deployment OK. Update Twilio webhook to:")
        print(f"  {BASE}/bot")
        print("\nCompare hola ms vs local+ngrok baseline (~2362 ms pre-optimizations).")
        return 0

    print("Deployment verify FAILED.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
