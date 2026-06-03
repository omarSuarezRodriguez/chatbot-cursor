"""Fase 3: benchmark final + anti-overfit + reporte antes/después."""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.benchmark_corpus_95 import (  # noqa: E402
    category_bucket,
    evaluate_row,
    extract_log_messages,
    load_menu,
    menu_tokens,
    pct_ok,
    run_corpus,
    run_logs,
    write_report,
)
from app.core.parser import OrderIntelligenceEngine, OrderParser  # noqa: E402

CORPUS_CSV = ROOT / "data" / "parser_corpus_95_coverage.csv"
ANTI_OVERFIT_CSV = ROOT / "data" / "parser_anti_overfit_20.csv"
ANTI_OVERFIT_TXT = ROOT / "data" / "parser_anti_overfit_20.txt"
OUT_REPORT = ROOT / "data" / "parser_phase3_report.md"
OUT_FAILURES_APPEND = ROOT / "data" / "parser_corpus_95_failures_new.csv"
OUT_BENCHMARK = ROOT / "data" / "parser_corpus_95_benchmark_report.md"

BASELINE_FASE1: Dict[str, float] = {
    "global": 88.8,
    "intent_global": 98.0,
    "pedido_productos": 86.5,
    "a_f": 87.4,
    "A": 94.7,
    "B": 85.9,
    "C": 89.3,
    "D": 72.4,
    "E": 100.0,
    "F": 86.7,
    "G": 84.0,
    "H": 90.7,
}


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_rows(
    rows: List[Dict[str, str]],
    menu: List[Dict[str, Any]],
    engine: OrderIntelligenceEngine,
    parser: OrderParser,
    mtoks: set[str],
) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    by_cat: Dict[str, List[bool]] = defaultdict(list)
    by_intent: Dict[str, List[bool]] = defaultdict(list)
    global_intent_rows: List[bool] = []
    order_rows: List[bool] = []

    for row in rows:
        ok, got, check_type, reason = evaluate_row(row, menu, mtoks, engine, parser)
        by_cat[category_bucket(row["categoria"])].append(ok)
        by_intent[row["intencion_esperada"]].append(ok)
        if row["intencion_esperada"] in {
            "menu",
            "pedido",
            "reservar",
            "inicio",
            "cancelar",
        }:
            global_intent_rows.append(ok)
        if row["intencion_esperada"] == "pedido_con_productos":
            order_rows.append(ok)
        if not ok:
            failures.append(
                {
                    "id": row.get("id", ""),
                    "categoria": row["categoria"],
                    "mensaje": row["mensaje"],
                    "intencion_esperada": row["intencion_esperada"],
                    "obtenido": got,
                    "check_type": check_type,
                    "causa_probable": reason or row.get("notas", ""),
                }
            )

    total = len(rows)
    return {
        "total": total,
        "failures": failures,
        "by_cat": {k: (sum(v), len(v)) for k, v in by_cat.items()},
        "by_intent": {k: (sum(v), len(v)) for k, v in by_intent.items()},
        "global_intent_pct": (
            100.0 * sum(global_intent_rows) / len(global_intent_rows)
            if global_intent_rows
            else 0.0
        ),
        "order_pct": (
            100.0 * sum(order_rows) / len(order_rows) if order_rows else 0.0
        ),
        "ok_count": total - len(failures),
    }


def af_pct(result: Dict[str, Any]) -> float:
    cats = ["A", "B", "C", "D", "E", "F"]
    ok = sum(result["by_cat"].get(c, (0, 0))[0] for c in cats)
    n = sum(result["by_cat"].get(c, (0, 0))[1] for c in cats)
    return 100.0 * ok / n if n else 0.0


def write_phase3_report(
    corpus: Dict[str, Any],
    anti: Dict[str, Any],
    logs: Dict[str, Any],
) -> None:
    total = corpus["total"]
    ok_total = total - len(corpus["failures"])
    overall = 100.0 * ok_total / total if total else 0.0
    anti_ok = anti["ok_count"]
    anti_total = anti["total"]
    anti_pct = 100.0 * anti_ok / anti_total if anti_total else 0.0

    lines = [
        "# Fase 3 — Validación final",
        "",
        "## Resumen ejecutivo",
        "",
        f"- **Corpus original:** {ok_total}/{total} ({overall:.1f}%)",
        f"- **Anti-overfit (20 frases nuevas):** {anti_ok}/{anti_total} ({anti_pct:.1f}%)",
        f"- **Intención global:** {corpus['global_intent_pct']:.1f}%",
        f"- **Pedido con productos:** {corpus['order_pct']:.1f}%",
        f"- **Categorías A–F:** {af_pct(corpus):.1f}%",
        "",
        "## Tabla antes / después (% por categoría)",
        "",
        "| Categoría | Fase 1 (baseline) | Fase 3 (actual) | Δ |",
        "|-----------|-------------------|-----------------|---|",
    ]

    for cat in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        before = BASELINE_FASE1.get(cat, 0.0)
        pair = corpus["by_cat"].get(cat, (0, 0))
        after = pct_ok(pair)
        delta = after - before
        sign = "+" if delta >= 0 else ""
        lines.append(f"| {cat} | {before:.1f}% | {after:.1f}% | {sign}{delta:.1f}pp |")

    lines.extend(
        [
            "",
            "## Tabla antes / después (métricas globales)",
            "",
            "| Métrica | Fase 1 | Fase 3 | Δ |",
            "|---------|--------|--------|---|",
            f"| Global | {BASELINE_FASE1['global']:.1f}% | {overall:.1f}% | "
            f"+{overall - BASELINE_FASE1['global']:.1f}pp |",
            f"| Intención global | {BASELINE_FASE1['intent_global']:.1f}% | "
            f"{corpus['global_intent_pct']:.1f}% | "
            f"+{corpus['global_intent_pct'] - BASELINE_FASE1['intent_global']:.1f}pp |",
            f"| Pedido+productos | {BASELINE_FASE1['pedido_productos']:.1f}% | "
            f"{corpus['order_pct']:.1f}% | "
            f"+{corpus['order_pct'] - BASELINE_FASE1['pedido_productos']:.1f}pp |",
            f"| A–F combinado | {BASELINE_FASE1['a_f']:.1f}% | {af_pct(corpus):.1f}% | "
            f"+{af_pct(corpus) - BASELINE_FASE1['a_f']:.1f}pp |",
            "",
            "## Por intención (corpus 3300)",
            "",
        ]
    )

    intent_sorted = sorted(
        corpus["by_intent"].items(),
        key=lambda x: x[1][0] / x[1][1] if x[1][1] else 1,
    )
    for intent, pair in intent_sorted:
        ok, n = pair
        lines.append(f"- **{intent}:** {100.0 * ok / n:.1f}% ({ok}/{n})")

    lines.extend(["", "## Anti-overfit (20 frases fuera del corpus)", ""])
    if anti["failures"]:
        lines.append(f"**Fallos:** {len(anti['failures'])}/{anti_total}")
        for fail in anti["failures"]:
            lines.append(
                f"- `{fail['mensaje'][:70]}` → {fail['obtenido']} ({fail['causa_probable']})"
            )
    else:
        lines.append("**Sin fallos** — no hay señales fuertes de overfitting al corpus.")

    lines.extend(
        [
            "",
            "## Logs reales",
            "",
            f"- Mensajes extraídos: {logs['count']}",
            f"- Con comando inferido: {logs['with_command']}",
            f"- Parse OK (producto en menú): {logs['anchored_parse_ok_pct']:.1f}%",
            "",
            "## Prueba manual WhatsApp",
            "",
            "Ver `data/parser_whatsapp_manual_10.md` (10 frases listas para copiar).",
            "",
        ]
    )

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


def append_new_failures(
    corpus_failures: List[Dict[str, Any]],
    anti_failures: List[Dict[str, Any]],
    existing_messages: Set[str],
) -> int:
    new_rows: List[Dict[str, Any]] = []
    for fail in corpus_failures + anti_failures:
        msg = fail.get("mensaje", "")
        if msg and msg not in existing_messages:
            origin = "anti_overfit" if str(fail.get("categoria", "")).startswith("I_") else "corpus"
            new_rows.append({**fail, "origen": origin})

    header = "id,categoria,mensaje,intencion_esperada,obtenido,check_type,causa_probable,origen\n"
    if not new_rows:
        OUT_FAILURES_APPEND.write_text(header, encoding="utf-8")
        return 0

    fieldnames = list(new_rows[0].keys())
    with open(OUT_FAILURES_APPEND, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)
    return len(new_rows)


def export_anti_overfit_txt(rows: List[Dict[str, str]]) -> None:
    ANTI_OVERFIT_TXT.write_text(
        "\n".join(row["mensaje"] for row in rows) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    menu = load_menu()
    mtoks = menu_tokens(menu)
    engine = OrderIntelligenceEngine(menu)
    parser = OrderParser(menu)

    corpus_rows = load_csv_rows(CORPUS_CSV)
    anti_rows = load_csv_rows(ANTI_OVERFIT_CSV)
    export_anti_overfit_txt(anti_rows)

    existing_messages = {row["mensaje"] for row in corpus_rows}

    print("=== Fase 3: corpus 3300 ===")
    corpus = run_corpus(menu, engine, parser, mtoks)
    total = corpus["total"]
    ok_total = total - len(corpus["failures"])
    print(f"OK: {ok_total}/{total} ({100 * ok_total / total:.1f}%)")

    print("\n=== Fase 3: anti-overfit 20 ===")
    anti = run_rows(anti_rows, menu, engine, parser, mtoks)
    print(
        f"OK: {anti['ok_count']}/{anti['total']} "
        f"({100 * anti['ok_count'] / anti['total']:.1f}%)"
    )

    log_msgs = extract_log_messages(100)
    logs = run_logs(log_msgs, menu, engine, parser, mtoks)

    write_report(corpus, logs)
    write_phase3_report(corpus, anti, logs)

    new_count = append_new_failures(
        corpus["failures"],
        anti["failures"],
        existing_messages,
    )

    print(f"\nReporte Fase 3: {OUT_REPORT}")
    print(f"Benchmark corpus: {OUT_BENCHMARK}")
    print(f"Fallos nuevos (append): {new_count} -> {OUT_FAILURES_APPEND}")


if __name__ == "__main__":
    main()
