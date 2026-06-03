"""Prueba rápida con mensajes inventados (no del corpus)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.parser import OrderIntelligenceEngine, OrderParser, infer_user_intent
from app.utils.validators import is_confirmation, is_greeting, is_rejection

MENU_PATH = ROOT / "data" / "menu_cache.json"

CASOS = [
    ("saludo", "buenas tardes amigo", None),
    ("menu", "a ver que tienen de comida", None),
    ("pedido vacio", "tengo mucha hambre", None),
    ("cancelar", "mejor ya no sigo con este pedido", None),
    ("inicio", "menu principal porfa", None),
    ("reservar", "quiero reservar mesa para 5", None),
    ("dato reserva", "reserva manana a las 8 pm para 4", None),
    ("pedido NL", "che ponme 2 hawaianas y 3 cocacolas bien frias", None),
    ("pedido typo", "dame una hawaina y un refresco", None),
    ("parcial bebida", "solo una bebida porfa", None),
    ("mezcla broma", "cancelar es broma dame 1 pizza hawaiana y 2 sodas", None),
    ("menu+pedido", "ver carta y tambien quiero una hawaiana", None),
    ("carrito agregar", "agrega una cocacola", "cart"),
    ("carrito otra", "otra hawaiana", "cart"),
    ("carrito quitar", "sin hawaiana", "cart"),
    ("confirmar", "va perfecto confirmemos", None),
    ("rechazar", "mejor no gracias", None),
    ("ruido", "a que hora cierran?", None),
    ("fuera menu", "5 pizzas pepperoni extra queso", None),
    ("ambiguo", "f", None),
]


def main() -> None:
    menu = json.loads(MENU_PATH.read_text(encoding="utf-8"))
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

    print("=" * 72)
    print("PRUEBA CON DATOS INVENTADOS — menu: Hawaiana + cocacola")
    print("=" * 72)

    ok = 0
    total = len(CASOS)

    for etiqueta, msg, modo in CASOS:
        print(f'\n--- [{etiqueta}] "{msg}"')
        intent = infer_user_intent(msg, menu_items=menu)
        cmd = intent.get("command")
        conf = float(intent.get("confidence") or 0)
        cmd_label = cmd if cmd else "-"
        print(
            f"  Intencion: {cmd_label}  conf={conf:.2f}  "
            f"productos={intent.get('has_products')}"
        )

        if modo == "cart":
            result = parser.apply_message(msg, cart)
            items = result.get("items") or []
            pairs = [(i["product"], i["qty"]) for i in items]
            print(f"  Carrito: {pairs}")
            if result.get("notes"):
                print(f"  Notas: {result['notes']}")
            if result.get("unknown"):
                print(f"  Unknown: {result['unknown']}")
            passed = bool(result.get("notes")) or pairs != [("Hawaiana", 1)]
            ok += int(passed)
            print(f"  Resultado: {'OK' if passed else 'REVISAR'}")
            continue

        parsed = engine.parse(msg)
        items = parsed.get("items") or []
        prod = [(i["product"], i["quantity"]) for i in items]
        print(f"  Parse: status={parsed.get('status')}  items={prod or []}")
        unknown = parsed.get("unknown") or []
        if unknown:
            print(f"  Unknown: {unknown[:3]}")
        internal = parsed.get("_internal") or {}
        if internal.get("user_intent"):
            print(f"  Intent interno: {internal['user_intent']}")

        passed = True
        if etiqueta == "saludo":
            passed = is_greeting(msg)
            print(f"  is_greeting: {is_greeting(msg)}")
        elif etiqueta == "confirmar":
            passed = is_confirmation(msg)
            print(f"  is_confirmation: {is_confirmation(msg)}")
        elif etiqueta == "rechazar":
            passed = is_rejection(msg)
            print(f"  is_rejection: {is_rejection(msg)}")
        elif etiqueta in ("menu", "pedido vacio", "cancelar", "inicio", "reservar"):
            passed = cmd == etiqueta.split()[0] or (
                etiqueta == "pedido vacio" and cmd == "pedido"
            )
        elif etiqueta == "dato reserva":
            passed = cmd is None
        elif etiqueta == "pedido NL":
            passed = len(prod) >= 2 and parsed.get("status") == "ok"
        elif etiqueta == "pedido typo":
            passed = len(prod) >= 2
        elif etiqueta == "parcial bebida":
            passed = parsed.get("status") == "needs_clarification" and len(prod) >= 1
        elif etiqueta == "mezcla broma":
            passed = len(prod) >= 2 and "Hawaiana" in {p[0] for p in prod}
        elif etiqueta == "menu+pedido":
            passed = len(prod) >= 1 and internal.get("user_intent") not in {
                "cancelar",
                "menu",
            }
        elif etiqueta == "ruido":
            passed = len(prod) == 0
        elif etiqueta == "fuera menu":
            passed = parsed.get("status") != "ok" or len(prod) == 0
        elif etiqueta == "ambiguo":
            passed = len(prod) == 0

        ok += int(passed)
        print(f"  Resultado: {'OK' if passed else 'REVISAR'}")

    print("\n" + "=" * 72)
    print(f"RESUMEN: {ok}/{total} casos inventados pasaron ({100*ok/total:.0f}%)")
    print("=" * 72)


if __name__ == "__main__":
    main()
