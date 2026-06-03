"""Compare realistic vs adversarial parser stress corpora; write CSVs."""
from __future__ import annotations

import csv
import json
import time
from collections import Counter
from pathlib import Path

from app.core.parser import OrderIntelligenceEngine, _DEMO_VALIDATION_MENU

ROOT = Path(__file__).resolve().parent.parent / "data"

CORPORA = [
    ("realistic", ROOT / "parser_stress_200_realistic.txt", ROOT / "parser_stress_200_realistic_results.csv"),
    ("adversarial_2k", ROOT / "parser_stress_2000.txt", ROOT / "parser_stress_2000_results.csv"),
]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[idx]


def run_corpus(name: str, path: Path, menu: list, menu_label: str) -> dict:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    engine = OrderIntelligenceEngine(menu)
    rows: list[dict] = []
    times: list[float] = []
    counts: Counter = Counter()

    for index, phrase in enumerate(lines, 1):
        started = time.perf_counter()
        result = engine.parse(phrase)
        elapsed_ms = (time.perf_counter() - started) * 1000
        times.append(elapsed_ms)

        internal = result.get("_internal") or {}
        status = result.get("status", "")
        counts[status] += 1
        if internal.get("fail_safe"):
            counts["fail_safe"] += 1
        if result.get("unknown"):
            counts["has_unknown"] += 1

        rows.append(
            {
                "linea": index,
                "frase": phrase,
                "corpus": name,
                "menu": menu_label,
                "status": status,
                "items": json.dumps(result.get("items", []), ensure_ascii=False),
                "unknown": json.dumps(result.get("unknown", []), ensure_ascii=False),
                "needs_review": internal.get("needs_review", False),
                "fail_safe": internal.get("fail_safe", False),
                "tiempo_ms": round(elapsed_ms, 3),
            }
        )

    total = len(lines)
    return {
        "corpus": name,
        "menu": menu_label,
        "n": total,
        "ok": counts["ok"],
        "needs": counts["needs_clarification"],
        "has_unknown": counts["has_unknown"],
        "fail_safe": counts["fail_safe"],
        "pct_ok": round(100 * counts["ok"] / total, 2) if total else 0.0,
        "p50": round(percentile(times, 50), 3),
        "p95": round(percentile(times, 95), 3),
        "max": round(max(times) if times else 0.0, 3),
        "rows": rows,
        "out_path": None,
    }


def main() -> None:
    real_menu = json.loads((ROOT / "menu_cache.json").read_text(encoding="utf-8"))
    menus = [("real", real_menu), ("demo", _DEMO_VALIDATION_MENU)]
    summaries: list[dict] = []
    by_key: dict[tuple[str, str], dict] = {}

    for corpus_name, corpus_path, out_path in CORPORA:
        combined_rows: list[dict] = []
        for menu_label, menu in menus:
            summary = run_corpus(corpus_name, corpus_path, menu, menu_label)
            summary["out_path"] = out_path
            summaries.append(summary)
            by_key[(corpus_name, menu_label)] = summary
            combined_rows.extend(summary["rows"])

        fieldnames = list(combined_rows[0].keys()) if combined_rows else []
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(combined_rows)
        print(f"Wrote {out_path.name} ({len(combined_rows)} rows)")

    print()
    print("Corpus          Menu   N     ok%   needs  unk  fail  p50    p95    max")
    for summary in summaries:
        print(
            f"{summary['corpus']:<15} {summary['menu']:<5} {summary['n']:<5} "
            f"{summary['pct_ok']:>5}% {summary['needs']:<5} {summary['has_unknown']:<4} "
            f"{summary['fail_safe']:<4} {summary['p50']:<6} {summary['p95']:<6} {summary['max']:<6}"
        )

    for menu_label in ("real", "demo"):
        realistic = by_key[("realistic", menu_label)]
        adversarial = by_key[("adversarial_2k", menu_label)]
        delta = round(realistic["pct_ok"] - adversarial["pct_ok"], 2)
        ratio = round(realistic["pct_ok"] / adversarial["pct_ok"], 2) if adversarial["pct_ok"] else 0.0
        print(f"Delta {menu_label}: realistas +{delta} pp ok (~{ratio}x vs adversarial)")


if __name__ == "__main__":
    main()
