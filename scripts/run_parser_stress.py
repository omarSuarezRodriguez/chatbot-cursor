"""Run parser stress test; writes data/parser_stress_2000_results.csv."""
from __future__ import annotations

import csv
import json
import re
import statistics
import time
from pathlib import Path

from app.core.parser import (
    OrderIntelligenceEngine,
    OrderParser,
    _DEMO_VALIDATION_MENU,
)

ROOT = Path(__file__).resolve().parent.parent
STRESS_PATH = ROOT / "data" / "parser_stress_2000.txt"
MENU_PATH = ROOT / "data" / "menu_cache.json"
OUT_PATH = ROOT / "data" / "parser_stress_2000_results.csv"

CART_EXAMPLE = [
    {
        "product_id": "2",
        "product": "cocacola",
        "qty": 2,
        "unit_price": 3.0,
        "subtotal": 6.0,
    },
    {
        "product_id": "1",
        "product": "Hawaiana",
        "qty": 1,
        "unit_price": 125.0,
        "subtotal": 125.0,
    },
]

CART_OP_RE = re.compile(
    r"\b(?:quita|quitame|quítame|cambia|reemplaza|en\s+vez\s+de|ya\s+no\s+quiero|"
    r"sacame|sácame|borra|agrega|agregar|añade|añadir)\b",
    re.IGNORECASE,
)

ADMIN_RE = re.compile(r"\b(?:CONFIRMAR\s+ORD|mesa\s+\d|anota:|telefonico)\b", re.I)
MENU_PHRASES = (
    "menu", "menú", "carta", "que tienen", "que hay", "catalogo", "mostrar menu", "ver la carta",
)
ORDER_EMPTY = ("tengo hambre", "quiero comer", "hacer pedido", "quisiera pedir")
GIBBERISH = re.compile(r"^(?:asdf|kkkk|xyz|jajaja|\?{2,}|\.\.\.)$", re.I)


def load_menu() -> list:
    if MENU_PATH.exists():
        return json.loads(MENU_PATH.read_text(encoding="utf-8"))
    return []


def menu_tokens(menu: list) -> set[str]:
    tokens: set[str] = set()
    for item in menu:
        name = str(item.get("nombre", "")).lower()
        for part in re.sub(r"[^\w\s]", " ", name).split():
            if len(part) >= 3:
                tokens.add(part)
    return tokens


def phrase_has_menu_product(phrase: str, mtoks: set[str]) -> bool:
    low = phrase.lower()
    return any(t in low for t in mtoks)


def tag_failures(phrase: str, result: dict, mtoks: set[str]) -> str:
    tags: list[str] = []
    low = phrase.lower()
    internal = result.get("_internal") or {}
    unknown = result.get("unknown") or []
    status = result.get("status", "")

    if ADMIN_RE.search(phrase):
        tags.append("admin_ruido")
    if any(p in low for p in MENU_PHRASES) and result.get("total_items", 0) == 0:
        tags.append("intencion_menu")
    if any(p in low for p in ORDER_EMPTY) and result.get("total_items", 0) == 0:
        tags.append("intencion_pedido_vacio")
    if GIBBERISH.match(low.strip()) or (len(low) < 4 and status != "ok"):
        tags.append("gibberish_ok")
    if internal.get("fail_safe"):
        tags.append("gibberish_ok")
    if phrase_has_menu_product(phrase, mtoks) and status != "ok":
        tags.append("producto_no_menu")
    elif phrase_has_menu_product(phrase, mtoks) and unknown:
        tags.append("producto_no_menu")
    if internal.get("ambiguous") or internal.get("needs_review"):
        tags.append("ambiguedad")
    if " con " in low and unknown:
        tags.append("conector_con_rompe")
    if re.search(r"\b(?:hamburguesa|pizza|refresco|cola)\b", low) and not phrase_has_menu_product(phrase, mtoks):
        if "hamburguesa" in low or "pizza" in low:
            tags.append("categoria_generica")
    if re.search(r"\b(?:unos cuantos|mitad de|veinti)", low):
        tags.append("fraccion_cantidad")
    if re.search(r"\bveinti\w+", low):
        tags.append("numero_palabra_limite")
    if re.search(r"\b(?:refresco|gaseosa|burger|soda)\b", low) and status != "ok":
        tags.append("sinonimo_incorrecto")
    if re.search(r"\b(?:eso|lo mismo|la que tiene)\b", low):
        tags.append("referencia_vaga")
    if CART_OP_RE.search(phrase):
        tags.append("cart_op")
    if not tags and status != "ok":
        tags.append("typo_sin_match")
    return "|".join(tags) if tags else ""


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[idx]


def run_stress(menu: list, label: str) -> dict:
    phrases = STRESS_PATH.read_text(encoding="utf-8").splitlines()
    engine = OrderIntelligenceEngine(menu)
    parser = OrderParser(menu)
    mtoks = menu_tokens(menu)
    rows = []
    times: list[float] = []
    ok = needs = 0

    for i, phrase in enumerate(phrases, 1):
        phrase = phrase.strip()
        if not phrase:
            continue
        t0 = time.perf_counter()
        result = engine.parse(phrase)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        times.append(elapsed_ms)

        if result.get("status") == "ok":
            ok += 1
        else:
            needs += 1

        internal = result.get("_internal") or {}
        tags = tag_failures(phrase, result, mtoks)

        cart_note = ""
        if CART_OP_RE.search(phrase):
            t1 = time.perf_counter()
            cart_res = parser.apply_message(phrase, CART_EXAMPLE)
            elapsed_ms = max(elapsed_ms, (time.perf_counter() - t1) * 1000)
            cart_note = json.dumps(cart_res.get("items", []), ensure_ascii=False)

        rows.append(
            {
                "linea": i,
                "frase": phrase,
                "menu": label,
                "status": result.get("status", ""),
                "items": json.dumps(result.get("items", []), ensure_ascii=False),
                "unknown": json.dumps(result.get("unknown", []), ensure_ascii=False),
                "needs_review": internal.get("needs_review", False),
                "fail_safe": internal.get("fail_safe", False),
                "tiempo_ms": round(elapsed_ms, 3),
                "tags_fallo": tags,
                "cart_result": cart_note,
            }
        )

    total = ok + needs
    return {
        "label": label,
        "rows": rows,
        "ok": ok,
        "needs": needs,
        "total": total,
        "pct_ok": round(100 * ok / total, 2) if total else 0,
        "p50": round(percentile(times, 50), 3),
        "p95": round(percentile(times, 95), 3),
        "max": round(max(times) if times else 0, 3),
    }


def main() -> None:
    real_menu = load_menu()
    summaries = []
    all_rows: list[dict] = []

    for label, menu in (("real", real_menu), ("demo", _DEMO_VALIDATION_MENU)):
        s = run_stress(menu, label)
        summaries.append(s)
        all_rows.extend(s["rows"])

    fieldnames = [
        "linea", "frase", "menu", "status", "items", "unknown",
        "needs_review", "fail_safe", "tiempo_ms", "tags_fallo", "cart_result",
    ]
    with OUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} rows to {OUT_PATH}")
    for s in summaries:
        print(
            f"[{s['label']}] ok={s['ok']}/{s['total']} ({s['pct_ok']}%) "
            f"lat p50={s['p50']}ms p95={s['p95']}ms max={s['max']}ms"
        )


if __name__ == "__main__":
    main()
