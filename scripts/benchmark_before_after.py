"""Before/after benchmark for session optimizations.

Simulates legacy behavior (always disk on touch, old patch_data path)
vs current optimized code. Also compares against documented production baseline.

Usage:
    python scripts/benchmark_before_after.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os_environ = __import__("os").environ
os_environ.setdefault("TWILIO_REST_WEBHOOK_REPLIES", "0")

from app.app import create_app  # noqa: E402
from app.core.state_manager import DEFAULT_STATE, StateManager  # noqa: E402
from app.integrations.google_sheets import (  # noqa: E402
    GoogleSheetsClient,
    get_google_sheets_client,
)

DOCUMENTED_BASELINE_MS = {
    "hola": 2362,
    "menu": 1179,
    "pedido_flow": 1202,
}
ITERATIONS = 25
TOUCH_MESSAGES = 20
REPORT_PATH = ROOT / "data" / "benchmark_before_after.json"


def _pct_improvement(before: float, after: float) -> float:
    if before <= 0:
        return 0.0
    return round(((before - after) / before) * 100, 1)


def _factor(before: float, after: float) -> str:
    if after <= 0:
        return "n/a"
    return f"{before / after:.0f}x"


def _stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "mean": 0.0}
    ordered = sorted(values)
    p95_idx = max(0, int(len(ordered) * 0.95) - 1)
    return {
        "p50": round(statistics.median(ordered), 2),
        "p95": round(ordered[p95_idx], 2),
        "mean": round(statistics.mean(ordered), 2),
    }


def _legacy_patch_data(state: StateManager, wa_id: str, **fields: Any) -> Dict[str, Any]:
    """Pre-optimization: get() + update() — double deepcopy."""
    current = state.get(wa_id)
    merged = {**current.get("data", {}), **fields}
    return state.update(wa_id, data=merged)


def _legacy_upsert_always_save(
    original: Callable[..., None],
) -> Callable[..., None]:
    def wrapper(self: GoogleSheetsClient, *args: Any, **kwargs: Any) -> None:
        original(self, *args, **kwargs)
        if self._connected:
            self._save_local_users()

    return wrapper


def _measure_flow(client, wa_id: str) -> Dict[str, float]:
    timings: Dict[str, float] = {}
    for label, body in [
        ("hola", "hola"),
        ("menu", "menu"),
        ("pedido_flow", "1 hamburguesa"),
    ]:
        if label == "pedido_flow":
            client.post(
                "/bot",
                data={"WaId": wa_id, "ProfileName": "Bench", "Body": "pedido"},
            )
        started = time.perf_counter()
        response = client.post(
            "/bot",
            data={"WaId": wa_id, "ProfileName": "Bench", "Body": body},
        )
        timings[label] = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            raise RuntimeError(f"{label} failed: HTTP {response.status_code}")
    return timings


def _run_latency_benchmark(client_factory, label: str) -> Dict[str, Any]:
    all_runs: Dict[str, List[float]] = {
        "hola": [],
        "menu": [],
        "pedido_flow": [],
    }
    for _ in range(ITERATIONS):
        wa_id = f"bench_{label}_{uuid.uuid4().hex[:8]}"
        timings = _measure_flow(client_factory(), wa_id)
        for key, ms in timings.items():
            all_runs[key].append(ms)
    return {key: _stats(values) for key, values in all_runs.items()}


def _count_touch_disk_writes(sheets: GoogleSheetsClient, legacy: bool) -> int:
    counter = {"n": 0}
    original_save = sheets._save_local_users

    def counting_save() -> None:
        counter["n"] += 1
        return original_save()

    sheets._save_local_users = counting_save  # type: ignore[method-assign]
    wa_id = f"touch_bench_{uuid.uuid4().hex[:8]}"

    for i in range(TOUCH_MESSAGES):
        sheets.upsert_user(wa_id=wa_id, name="First")
        if legacy and i > 0:
            sheets._save_local_users()

    sheets._save_local_users = original_save  # type: ignore[method-assign]
    return counter["n"]


def _benchmark_patch_data(legacy: bool, iterations: int = 500) -> float:
    state = StateManager(persist_path=None)
    wa_id = "patch_bench"
    state.update(wa_id, flow="order", step="collect_items", data={"cart": []})
    if legacy:
        def patch_fn(**kw: Any) -> Dict[str, Any]:
            return _legacy_patch_data(state, wa_id, **kw)
    else:
        def patch_fn(**kw: Any) -> Dict[str, Any]:
            return state.patch_data(wa_id, **kw)

    started = time.perf_counter()
    for i in range(iterations):
        patch_fn(turn=i)
    return (time.perf_counter() - started) * 1000


def _benchmark_append_row_lookup(sheets: GoogleSheetsClient) -> Dict[str, float]:
    """Compare get_all_values vs col_values for row index (simulated cost)."""
    results: Dict[str, float] = {}
    if not sheets._connected:
        return {"get_all_values_ms": 0.0, "col_values_ms": 0.0, "skipped": True}

    sheet = sheets._get_sheet("USERS")
    if not sheet:
        return {"get_all_values_ms": 0.0, "col_values_ms": 0.0, "skipped": True}

    started = time.perf_counter()
    for _ in range(5):
        len(sheet.get_all_values())
    results["get_all_values_ms"] = round(
        (time.perf_counter() - started) * 1000 / 5, 2
    )

    started = time.perf_counter()
    for _ in range(5):
        len(sheet.col_values(1))
    results["col_values_ms"] = round((time.perf_counter() - started) * 1000 / 5, 2)
    results["skipped"] = False
    return results


def main() -> int:
    print("=== Benchmark antes / después (optimizaciones sesión) ===\n")

    app = create_app()
    sheets = app.config["user_service"].sheets

    def make_client():
        return app.test_client()

    print(f"Midiendo latencia ({ITERATIONS} iteraciones por flujo)...")
    after_latency = _run_latency_benchmark(make_client, "after")

    legacy_upsert = GoogleSheetsClient.upsert_user
    with patch.object(
        GoogleSheetsClient,
        "upsert_user",
        _legacy_upsert_always_save(legacy_upsert),
    ):
        before_latency = _run_latency_benchmark(make_client, "before_legacy_touch")

    print("Midiendo escrituras a disco en touch repetido...")
    before_disk_writes = _count_touch_disk_writes(sheets, legacy=True)
    after_disk_writes = _count_touch_disk_writes(sheets, legacy=False)

    print("Midiendo patch_data (500 iteraciones)...")
    before_patch_ms = _benchmark_patch_data(legacy=True)
    after_patch_ms = _benchmark_patch_data(legacy=False)

    print("Midiendo lookup de fila en Sheets (5 repeticiones)...")
    append_lookup = _benchmark_append_row_lookup(sheets)

    latency_comparison = []
    for step in ("hola", "menu", "pedido_flow"):
        before_p50 = before_latency[step]["p50"]
        after_p50 = after_latency[step]["p50"]
        baseline = DOCUMENTED_BASELINE_MS[step]
        latency_comparison.append(
            {
                "step": step,
                "documented_baseline_ms": baseline,
                "before_session_p50_ms": before_p50,
                "after_session_p50_ms": after_p50,
                "session_improvement_pct": _pct_improvement(before_p50, after_p50),
                "total_vs_baseline_pct": _pct_improvement(baseline, after_p50),
                "total_factor_vs_baseline": _factor(baseline, after_p50),
            }
        )

    report = {
        "iterations": ITERATIONS,
        "touch_messages": TOUCH_MESSAGES,
        "latency": {
            "before_session": before_latency,
            "after_session": after_latency,
            "comparison": latency_comparison,
        },
        "touch_disk_writes": {
            "before": before_disk_writes,
            "after": after_disk_writes,
            "saved_per_conversation": before_disk_writes - after_disk_writes,
            "reduction_pct": _pct_improvement(
                float(before_disk_writes), float(after_disk_writes)
            ),
        },
        "patch_data_500_iters_ms": {
            "before": round(before_patch_ms, 2),
            "after": round(after_patch_ms, 2),
            "improvement_pct": _pct_improvement(before_patch_ms, after_patch_ms),
        },
        "append_row_lookup": append_lookup,
        "documented_baseline_ms": DOCUMENTED_BASELINE_MS,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\n{'Paso':<14} {'Baseline doc':>12} {'Antes ses.':>12} {'Después':>10} {'Sesión':>8} {'Total':>8}")
    print("-" * 72)
    for row in latency_comparison:
        print(
            f"{row['step']:<14} "
            f"{row['documented_baseline_ms']:>10.0f} ms "
            f"{row['before_session_p50_ms']:>10.1f} ms "
            f"{row['after_session_p50_ms']:>8.1f} ms "
            f"{row['session_improvement_pct']:>+6.1f}% "
            f"{row['total_vs_baseline_pct']:>+6.1f}%"
        )

    print(f"\nEscrituras disco en {TOUCH_MESSAGES} touch (mismo usuario):")
    print(f"  Antes:  {before_disk_writes} escrituras")
    print(f"  Después: {after_disk_writes} escrituras")
    print(
        f"  Ahorro: {before_disk_writes - after_disk_writes} escrituras "
        f"({report['touch_disk_writes']['reduction_pct']:+.1f}%)"
    )

    print(f"\npatch_data x500:")
    print(f"  Antes:  {before_patch_ms:.1f} ms")
    print(f"  Después: {after_patch_ms:.1f} ms")
    print(f"  Mejora: {report['patch_data_500_iters_ms']['improvement_pct']:+.1f}%")

    if not append_lookup.get("skipped"):
        print(f"\nLookup fila Sheets (promedio):")
        print(f"  get_all_values: {append_lookup['get_all_values_ms']:.1f} ms")
        print(f"  col_values(1):  {append_lookup['col_values_ms']:.1f} ms")

    print(f"\nReporte guardado: {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
