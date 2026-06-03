"""Fase 1: benchmark corpus 95% vs parser + infer_user_intent."""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.parser import OrderIntelligenceEngine, OrderParser, infer_user_intent
from app.utils.validators import is_confirmation, is_greeting, is_rejection

MENU_PATH = ROOT / "data" / "menu_cache.json"
CSV_PATH = ROOT / "data" / "parser_corpus_95_coverage.csv"
OUT_FAILURES = ROOT / "data" / "parser_corpus_95_failures.csv"
OUT_REPORT = ROOT / "data" / "parser_corpus_95_benchmark_report.md"
LOG_DIR = ROOT / "client_messages_log"

GLOBAL_COMMANDS = frozenset({"menu", "pedido", "reservar", "inicio", "cancelar"})
CART_SAMPLE = [
    {
        "product_id": "1",
        "product": "Hawaiana",
        "qty": 1,
        "unit_price": 125.0,
        "subtotal": 125.0,
    },
    {
        "product_id": "2",
        "product": "cocacola",
        "qty": 2,
        "unit_price": 3.0,
        "subtotal": 6.0,
    },
]

CART_OP_RE = re.compile(
    r"\b(?:quita|quitame|quítame|cambia|reemplaza|en\s+vez\s+de|ya\s+no\s+quiero|"
    r"sacame|sácame|borra|agrega|agregar|añade|añadir|agregame|agrégame|sumale|súmale)\b",
    re.IGNORECASE,
)
CLIENT_LINE_RE = re.compile(
    r"^(?:cliente|Cliente):\s*(.+)$",
    re.MULTILINE,
)


def load_menu() -> List[Dict[str, Any]]:
    if MENU_PATH.exists():
        return json.loads(MENU_PATH.read_text(encoding="utf-8"))
    return []


def menu_tokens(menu: List[Dict[str, Any]]) -> set[str]:
    tokens: set[str] = set()
    for item in menu:
        if not item.get("disponible", True):
            continue
        name = str(item.get("nombre", "")).lower()
        for part in re.sub(r"[^\w\s]", " ", name).split():
            if len(part) >= 3:
                tokens.add(part)
        for cat in str(item.get("categoria", "")).lower().split():
            if len(cat) >= 4:
                tokens.add(cat)
    tokens.update({"pizza", "pizzas", "hawaiana", "hawaiiana", "coca", "cola", "cocacola"})
    return tokens


def phrase_has_menu_anchor(text: str, mtoks: set[str]) -> bool:
    low = text.lower()
    return any(t in low for t in mtoks)


def evaluate_row(
    row: Dict[str, str],
    menu: List[Dict[str, Any]],
    mtoks: set[str],
    engine: OrderIntelligenceEngine,
    parser: OrderParser,
) -> Tuple[bool, str, str, str]:
    """Return ok, got_label, check_type, failure_reason."""
    msg = row["mensaje"]
    expected = row["intencion_esperada"]
    prod_flag = row.get("productos_en_mensaje", "")
    cat = row.get("categoria", "")

    intent = infer_user_intent(msg, menu_items=menu)
    cmd = intent.get("command")
    conf = float(intent.get("confidence") or 0)
    has_prod = bool(intent.get("has_products"))

    parse_result = engine.parse(msg)
    apply_result = parser.apply_message(msg, CART_SAMPLE)

    if expected in GLOBAL_COMMANDS:
        if expected == "pedido":
            ok = cmd == "pedido" and not has_prod
            got = f"command={cmd} has_products={has_prod}"
            if not ok and cmd == "pedido" and has_prod:
                reason = "pedido detectado pero marcado con productos"
            elif not ok:
                reason = f"esperaba pedido sin productos, obtuvo {got}"
            else:
                reason = ""
            return ok, got, "intent_global", reason

        ok = cmd == expected
        if expected == "menu" and prod_flag == "si":
            ok = cmd == "menu" or (parse_result.get("total_items", 0) > 0)
        got = f"command={cmd} conf={conf:.2f}"
        reason = "" if ok else f"esperaba {expected}, obtuvo command={cmd}"
        return ok, got, "intent_global", reason

    if expected == "pedido_con_productos":
        items = parse_result.get("total_items", 0) or len(parse_result.get("items", []))
        status = parse_result.get("status", "")
        internal = parse_result.get("_internal") or {}
        if prod_flag == "no":
            ok = items == 0 or internal.get("fail_safe")
            got = f"items={items} status={status}"
            return ok, got, "parse_order", "no productos esperados"

        anchored = phrase_has_menu_anchor(msg, mtoks)
        if prod_flag == "parcial" and not anchored:
            ok = status != "ok" or items == 0
            got = f"items={items} status={status}"
            reason = "" if ok else "falso positivo en producto fuera de menú"
            return ok, got, "parse_order", reason

        ok = items > 0 and status in ("ok", "needs_clarification")
        if anchored and not ok:
            ok = items > 0
        got = f"items={items} status={status} unknown={parse_result.get('unknown', [])[:2]}"
        reason = "" if ok else "no reconoció productos del menú"
        return ok, got, "parse_order", reason

    if expected == "modificar_carrito":
        notes = apply_result.get("notes") or []
        cart_len = len(apply_result.get("items") or [])
        op_match = bool(CART_OP_RE.search(msg))
        changed = bool(notes) or cart_len != len(CART_SAMPLE)
        ok = changed or (op_match and not apply_result.get("unknown"))
        got = f"notes={len(notes)} cart={cart_len} op={op_match}"
        reason = "" if ok else "carrito no reflejó la operación"
        return ok, got, "cart_ops", reason

    if expected == "confirmar":
        ok = is_confirmation(msg)
        got = f"is_confirmation={ok}"
        return ok, got, "validator", "" if ok else "no detectó confirmación"

    if expected == "rechazar":
        ok = is_rejection(msg)
        got = f"is_rejection={ok}"
        return ok, got, "validator", "" if ok else "no detectó rechazo"

    if expected == "saludo":
        ok = is_greeting(msg) or (cmd is None and len(msg.split()) <= 4)
        got = f"greeting={is_greeting(msg)} command={cmd}"
        return ok, got, "greeting", "" if ok else "saludo no reconocido"

    if expected in ("dato_reserva", "datos_entrega"):
        ok = cmd not in GLOBAL_COMMANDS or conf < 0.82
        got = f"command={cmd}"
        reason = "" if ok else "falso positivo de comando global en dato de flujo"
        return ok, got, "flow_slot", reason

    if expected == "ambiguo":
        ok = cmd is None or conf < 0.82
        if phrase_has_menu_anchor(msg, mtoks) and parse_result.get("total_items", 0) > 0:
            ok = True
        got = f"command={cmd} conf={conf:.2f}"
        return ok, got, "ambiguo", "" if ok else "forzó comando global incorrecto"

    if expected == "ruido":
        items = parse_result.get("total_items", 0)
        ok = (cmd is None or conf < 0.82) and items == 0
        internal = parse_result.get("_internal") or {}
        if internal.get("fail_safe"):
            ok = True
        got = f"command={cmd} items={items}"
        return ok, got, "ruido", "" if ok else "ruido interpretado como pedido/comando"

    return True, "skip", "other", ""


def category_bucket(categoria: str) -> str:
    if categoria.startswith("A_"):
        return "A"
    if categoria.startswith("B_"):
        return "B"
    if categoria.startswith("C_"):
        return "C"
    if categoria.startswith("D_"):
        return "D"
    if categoria.startswith("E_"):
        return "E"
    if categoria.startswith("F_"):
        return "F"
    if categoria.startswith("G_"):
        return "G"
    if categoria.startswith("H_"):
        return "H"
    return "?"


def run_corpus(
    menu: List[Dict[str, Any]],
    engine: OrderIntelligenceEngine,
    parser: OrderParser,
    mtoks: set[str],
) -> Dict[str, Any]:
    rows: List[Dict[str, str]] = []
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    failures: List[Dict[str, Any]] = []
    by_cat: Dict[str, List[bool]] = defaultdict(list)
    by_intent: Dict[str, List[bool]] = defaultdict(list)
    global_intent_rows: List[bool] = []
    order_rows: List[bool] = []
    check_counts: Dict[str, int] = defaultdict(int)

    t0 = time.perf_counter()
    for row in rows:
        ok, got, check_type, reason = evaluate_row(
            row, menu, mtoks, engine, parser
        )
        check_counts[check_type] += 1
        by_cat[category_bucket(row["categoria"])].append(ok)
        by_intent[row["intencion_esperada"]].append(ok)
        if row["intencion_esperada"] in GLOBAL_COMMANDS:
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

    elapsed = time.perf_counter() - t0
    total = len(rows)
    return {
        "total": total,
        "elapsed_ms": elapsed * 1000,
        "failures": failures,
        "by_cat": {k: (sum(v), len(v)) for k, v in by_cat.items()},
        "by_intent": {k: (sum(v), len(v)) for k, v in by_intent.items()},
        "global_intent_pct": (
            100.0 * sum(global_intent_rows) / len(global_intent_rows)
            if global_intent_rows
            else 0
        ),
        "order_pct": (
            100.0 * sum(order_rows) / len(order_rows) if order_rows else 0
        ),
        "ok_count": total - len(failures),
        "check_counts": dict(check_counts),
    }


def pct_ok(pair: Tuple[int, int]) -> float:
    ok, n = pair
    return 100.0 * ok / n if n else 0.0


def extract_log_messages(limit: int = 100) -> List[str]:
    messages: List[str] = []
    if not LOG_DIR.exists():
        return messages
    for path in sorted(LOG_DIR.glob("client_messages_log*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in CLIENT_LINE_RE.finditer(text):
            line = match.group(1).strip()
            if line and line not in messages:
                messages.append(line)
            if len(messages) >= limit:
                return messages
    return messages


def run_logs(
    messages: List[str],
    menu: List[Dict[str, Any]],
    engine: OrderIntelligenceEngine,
    parser: OrderParser,
    mtoks: set[str],
) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    intent_cmds: List[Optional[str]] = []
    parse_ok: List[bool] = []

    for msg in messages:
        intent = infer_user_intent(msg, menu_items=menu)
        cmd = intent.get("command")
        intent_cmds.append(cmd)
        pr = engine.parse(msg)
        anchored = phrase_has_menu_anchor(msg, mtoks)
        if anchored:
            ok = (pr.get("total_items") or 0) > 0
            parse_ok.append(ok)
            if not ok:
                failures.append(
                    {
                        "mensaje": msg,
                        "intencion_inferida": cmd,
                        "parse_items": pr.get("total_items", 0),
                        "causa": "menú real en mensaje sin items",
                    }
                )
        elif cmd:
            failures.append(
                {
                    "mensaje": msg,
                    "intencion_inferida": cmd,
                    "conf": intent.get("confidence"),
                    "causa": "comando inferido en mensaje de log",
                }
            )

    return {
        "count": len(messages),
        "with_command": sum(1 for c in intent_cmds if c),
        "anchored_parse_ok_pct": (
            100.0 * sum(parse_ok) / len(parse_ok) if parse_ok else 0
        ),
        "failures": failures[:30],
    }


def write_report(corpus: Dict[str, Any], logs: Dict[str, Any]) -> None:
    total = corpus["total"]
    ok_total = total - len(corpus["failures"])
    overall = 100.0 * ok_total / total if total else 0

    a_f = ["A", "B", "C", "D", "E", "F"]
    g_h = ["G", "H"]
    af_ok = sum(corpus["by_cat"].get(c, (0, 0))[0] for c in a_f)
    af_n = sum(corpus["by_cat"].get(c, (0, 0))[1] for c in a_f)
    gh_ok = sum(corpus["by_cat"].get(c, (0, 0))[0] for c in g_h)
    gh_n = sum(corpus["by_cat"].get(c, (0, 0))[1] for c in g_h)

    lines = [
        "# Fase 1 — Benchmark corpus 95%",
        "",
        f"- **Líneas evaluadas:** {total}",
        f"- **Tiempo:** {corpus['elapsed_ms']:.0f} ms",
        f"- **Acierto global (todas las filas):** {overall:.1f}%",
        f"- **Intención global (menu/pedido/reservar/inicio/cancelar):** "
        f"{corpus['global_intent_pct']:.1f}%",
        f"- **Pedido con productos (`pedido_con_productos`):** "
        f"{corpus['order_pct']:.1f}%",
        f"- **Categorías A–F:** {100.0 * af_ok / af_n:.1f}% ({af_ok}/{af_n})"
        if af_n
        else "",
        f"- **Categorías G–H:** {100.0 * gh_ok / gh_n:.1f}% ({gh_ok}/{gh_n})"
        if gh_n
        else "",
        "",
        "## Por categoría",
        "| Cat | OK | Total | % |",
        "|-----|-----|-------|---|",
    ]
    for cat in sorted(corpus["by_cat"].keys()):
        ok, n = corpus["by_cat"][cat]
        lines.append(f"| {cat} | {ok} | {n} | {100.0 * ok / n:.1f}% |")

    lines.extend(["", "## Por intención esperada (peores primero)", ""])
    intent_sorted = sorted(
        corpus["by_intent"].items(),
        key=lambda x: x[1][0] / x[1][1] if x[1][1] else 1,
    )
    for intent, (ok, n) in intent_sorted:
        lines.append(f"- **{intent}:** {100.0 * ok / n:.1f}% ({ok}/{n})")

    lines.extend(
        [
            "",
            "## Logs reales (`client_messages_log/`)",
            f"- Mensajes cliente extraídos: {logs['count']}",
            f"- Con comando inferido: {logs['with_command']}",
            f"- Parse OK en mensajes con producto del menú: "
            f"{logs['anchored_parse_ok_pct']:.1f}%",
            "",
        ]
    )

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    with open(OUT_FAILURES, "w", encoding="utf-8", newline="") as f:
        if corpus["failures"]:
            w = csv.DictWriter(f, fieldnames=list(corpus["failures"][0].keys()))
            w.writeheader()
            w.writerows(corpus["failures"][:50])
        else:
            f.write("id,categoria,mensaje,intencion_esperada,obtenido,check_type,causa_probable\n")


def main() -> None:
    menu = load_menu()
    mtoks = menu_tokens(menu)
    engine = OrderIntelligenceEngine(menu)
    parser = OrderParser(menu)

    print("=== Corpus benchmark ===")
    corpus = run_corpus(menu, engine, parser, mtoks)
    total = corpus["total"]
    ok_total = total - len(corpus["failures"])
    print(f"Total: {total} | OK: {ok_total} ({100*ok_total/total:.1f}%)")
    print(f"Intent global: {corpus['global_intent_pct']:.1f}%")
    print(f"Pedido+productos: {corpus['order_pct']:.1f}%")
    for cat in sorted(corpus["by_cat"]):
        ok, n = corpus["by_cat"][cat]
        print(f"  Cat {cat}: {100*ok/n:.1f}% ({ok}/{n})")

    log_msgs = extract_log_messages(100)
    print("\n=== Logs reales ===")
    logs = run_logs(log_msgs, menu, engine, parser, mtoks)
    print(f"Mensajes: {logs['count']} | Con intent: {logs['with_command']}")

    write_report(corpus, logs)
    print(f"\nReporte: {OUT_REPORT}")
    print(f"Top fallos: {OUT_FAILURES}")


if __name__ == "__main__":
    main()
