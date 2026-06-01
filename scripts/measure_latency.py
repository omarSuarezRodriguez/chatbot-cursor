"""Paso 1 / Paso 12 — measure POST /bot latency and compare to baseline.

Usage:
    python scripts/measure_latency.py
    DEPLOY_URL=https://your-app.onrender.com python scripts/measure_latency.py

Writes: data/latency_report.json
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASELINE_MS = {
    "hola": 2362,
    "menu": 1179,
    "pedido_flow": 1202,
}

TARGET_MS = 2000
REPORT_PATH = ROOT / "data" / "latency_report.json"


def _measure_with_test_client() -> dict[str, float]:
    from app.app import app

    wa_id = f"latency_{uuid.uuid4().hex[:8]}"
    timings: dict[str, float] = {}

    with app.test_client() as client:
        for label, body in [
            ("hola", "hola"),
            ("menu", "menu"),
            ("pedido", "pedido"),
            ("pedido_short", "1 hamburguesa"),
        ]:
            started = time.perf_counter()
            response = client.post(
                "/bot",
                data={"WaId": wa_id, "ProfileName": "Latency", "Body": body},
            )
            elapsed = (time.perf_counter() - started) * 1000
            if response.status_code != 200:
                raise RuntimeError(f"{label} failed: HTTP {response.status_code}")
            timings[label] = round(elapsed, 1)

    timings["pedido_flow"] = timings["pedido_short"]
    return timings


def _measure_with_http(base: str) -> dict[str, float]:
    wa_id = f"latency_{uuid.uuid4().hex[:8]}"
    timings: dict[str, float] = {}
    timeout = int(os.getenv("DEPLOY_TIMEOUT", "60"))

    for label, body in [
        ("hola", "hola"),
        ("menu", "menu"),
        ("pedido", "pedido"),
        ("pedido_short", "1 hamburguesa"),
    ]:
        started = time.perf_counter()
        response = requests.post(
            f"{base.rstrip('/')}/bot",
            data={"WaId": wa_id, "ProfileName": "Latency", "Body": body},
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            raise RuntimeError(f"{label} failed: HTTP {response.status_code}")
        timings[label] = round(elapsed, 1)

    timings["pedido_flow"] = timings["pedido_short"]
    return timings


def _pct_change(before: float, after: float) -> str:
    if before <= 0:
        return "n/a"
    delta = ((after - before) / before) * 100
    return f"{delta:+.0f}%"


def main() -> int:
    deploy_url = os.getenv("DEPLOY_URL", "").strip()
    mode = "http" if deploy_url else "test_client"
    target_label = deploy_url or "Flask test client (warm cache)"

    print("=== Latency measure (Paso 12) ===\n")
    print(f"Mode: {mode}")
    print(f"Target: {target_label}\n")

    if deploy_url:
        current = _measure_with_http(deploy_url)
    else:
        current = _measure_with_test_client()

    rows = []
    for key in ("hola", "menu", "pedido_flow"):
        before = BASELINE_MS[key]
        after = current[key]
        rows.append(
            {
                "step": key,
                "baseline_ms": before,
                "current_ms": after,
                "delta_pct": _pct_change(before, after),
                "under_2s": after < TARGET_MS,
            }
        )

    print(f"{'Step':<14} {'Baseline':>10} {'Now':>10} {'Change':>8} {'<2s':>5}")
    print("-" * 52)
    for row in rows:
        ok = "OK" if row["under_2s"] else "NO"
        print(
            f"{row['step']:<14} {row['baseline_ms']:>8.0f} ms "
            f"{row['current_ms']:>8.1f} ms {row['delta_pct']:>8} {ok:>5}"
        )

    pedido_ok = current["pedido_flow"] < TARGET_MS
    print()
    if pedido_ok:
        print(f"Meta OK: pedido normal {current['pedido_flow']:.0f} ms < {TARGET_MS} ms")
    else:
        print(
            f"Meta FAIL: pedido normal {current['pedido_flow']:.0f} ms "
            f">= {TARGET_MS} ms"
        )

    report = {
        "mode": mode,
        "target": target_label,
        "baseline_ms": BASELINE_MS,
        "current_ms": current,
        "comparison": rows,
        "target_ms": TARGET_MS,
        "meta_pedido_ok": pedido_ok,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nReport saved: {REPORT_PATH.relative_to(ROOT)}")
    return 0 if pedido_ok else 1


if __name__ == "__main__":
    sys.exit(main())
