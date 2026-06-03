"""Medir latencia del parser (infer + parse + apply)."""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.parser import OrderIntelligenceEngine, OrderParser, infer_user_intent

SAMPLES = [
    "hola",
    "menu",
    "dame 2 hawaianas y 3 cocacolas",
    "cancelar es broma dame 1 pizza hawaiana y 2 sodas",
    "reserva manana a las 8 pm para 4",
    "agrega una cocacola",
]


def stats(xs: list[float]) -> dict[str, float]:
    ordered = sorted(xs)
    return {
        "p50": statistics.median(ordered),
        "p95": ordered[int(len(ordered) * 0.95) - 1],
        "max": max(ordered),
        "avg": sum(ordered) / len(ordered),
    }


def main() -> None:
    menu = json.loads((ROOT / "data" / "menu_cache.json").read_text(encoding="utf-8"))
    engine = OrderIntelligenceEngine(menu)
    parser = OrderParser(menu)
    cart = [
        {
            "product_id": "1",
            "product": "Hawaiana",
            "qty": 1,
            "unit_price": 125.0,
            "subtotal": 125.0,
        },
    ]

    for sample in SAMPLES:
        infer_user_intent(sample, menu_items=menu)
        engine.parse(sample)

    lat_infer: list[float] = []
    lat_parse: list[float] = []
    lat_full: list[float] = []

    for _ in range(200):
        for sample in SAMPLES:
            t0 = time.perf_counter()
            infer_user_intent(sample, menu_items=menu)
            lat_infer.append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            engine.parse(sample)
            lat_parse.append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            infer_user_intent(sample, menu_items=menu)
            engine.parse(sample)
            parser.apply_message(sample, cart)
            lat_full.append((time.perf_counter() - t0) * 1000)

    print("=== Latencia por mensaje (6 frases x 200 iteraciones) ===")
    for name, values in [
        ("infer_user_intent", lat_infer),
        ("parse", lat_parse),
        ("infer+parse+apply", lat_full),
    ]:
        s = stats(values)
        print(
            f"{name}: p50={s['p50']:.2f}ms  p95={s['p95']:.2f}ms  "
            f"avg={s['avg']:.2f}ms  max={s['max']:.2f}ms"
        )

    rows = list(csv.DictReader(open(ROOT / "data" / "parser_corpus_95_coverage.csv", encoding="utf-8")))
    messages = [row["mensaje"] for row in rows]
    t0 = time.perf_counter()
    for message in messages:
        infer_user_intent(message, menu_items=menu)
        engine.parse(message)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print("\n=== Throughput corpus 3300 ===")
    print(f"Total infer+parse: {elapsed_ms:.0f} ms")
    print(f"Por mensaje: {elapsed_ms / len(messages):.2f} ms")


if __name__ == "__main__":
    main()
