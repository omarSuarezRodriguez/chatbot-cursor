"""Generate ≥3000 unique client messages + CSV for parser/intent coverage (~95%)."""
from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple

random.seed(20260604)

ROOT = Path(__file__).resolve().parent.parent
MENU_PATH = ROOT / "data" / "menu_cache.json"
OUT_TXT = ROOT / "data" / "parser_corpus_95_coverage.txt"
OUT_CSV = ROOT / "data" / "parser_corpus_95_coverage.csv"

TARGET = 3000
MAX_ATTEMPTS = 120_000

# Menu-anchored products (from menu_cache.json)
PIZZA_FORMS = [
    "hawaiana",
    "pizza hawaiana",
    "pizza hawaiiana",
    "hawaiiana",
    "piza hawaiana",
    "hawaiana pizza",
    "una hawaiana",
    "la hawaiana",
]
DRINK_FORMS = [
    "cocacola",
    "coca cola",
    "coca",
    "refresco",
    "soda",
    "una cocacola",
    "2 cocacolas",
]
CATEGORY_PHRASES = [
    "una pizza",
    "pizza",
    "una bebida",
    "bebida",
    "refresco",
    "algo de pizza",
    "algo de bebida",
]
TYPO_PIZZA = ["hawaiana", "hawaiano", "hawaiiana", "hawaina", "hawaianas"]
TYPO_DRINK = ["cocacola", "coca kola", "koka cola", "cocacolas"]

QTY = {
    1: ["1", "una", "un", "uno"],
    2: ["2", "dos", "un par de", "par de"],
    3: ["3", "tres"],
    4: ["4", "cuatro"],
    5: ["5", "cinco"],
    6: ["6", "seis"],
    8: ["8", "ocho"],
    10: ["10", "diez"],
    12: ["12", "doce", "una docena de", "docena de"],
}
QTY_X = ["{n}x {p}", "{n} x {p}", "{n}×{p}"]

PREFIX_ORDER = [
    "",
    "hola ",
    "buenas ",
    "oye ",
    "porfa ",
    "quisiera ",
    "quiero ",
    "dame ",
    "ponme ",
    "me traes ",
    "necesito ",
    "voy a querer ",
]
SEP = [" y ", ", ", " + ", " | ", " ; ", " tambien ", " ademas ", " luego "]
SUFFIX = ["", " porfa", " gracias", " plis", " para llevar", " nomás"]

MENU_INTENTS = [
    ("menu", "ver el menu"),
    ("menu", "ver la carta"),
    ("menu", "muestrame el menu"),
    ("menu", "que tienen"),
    ("menu", "que hay de comer"),
    ("menu", "pasame el menu"),
    ("menu", "precios"),
    ("menu", "catalogo"),
    ("menu", "lista de precios"),
    ("menu", "que me recomiendan"),
]
PEDIDO_INTENTS = [
    ("pedido", "quiero hacer un pedido"),
    ("pedido", "hacer pedido"),
    ("pedido", "ordenar"),
    ("pedido", "quiero ordenar"),
    ("pedido", "tengo hambre"),
    ("pedido", "quiero comer"),
    ("pedido", "voy a pedir"),
    ("pedido", "me gustaria pedir"),
]
RESERVAR_INTENTS = [
    ("reservar", "quiero reservar"),
    ("reservar", "reservar mesa"),
    ("reservar", "mesa para 4"),
    ("reservar", "necesito reservar"),
    ("reservar", "agendar mesa"),
    ("reservar", "mesa para 2 personas"),
]
INICIO_INTENTS = [
    ("inicio", "inicio"),
    ("inicio", "volver al inicio"),
    ("inicio", "reiniciar"),
    ("inicio", "empezar de nuevo"),
    ("inicio", "menu principal"),
]
CANCELAR_INTENTS = [
    ("cancelar", "cancelar"),
    ("cancelar", "cancelar pedido"),
    ("cancelar", "anular pedido"),
    ("cancelar", "ya no quiero el pedido"),
]

Record = Dict[str, str]


def _pick(seq: List[str]) -> str:
    return random.choice(seq)


def _qty_phrase(n: int, product: str) -> str:
    style = random.randint(0, 3)
    q = _pick(QTY.get(n, [str(n)]))
    if style == 0:
        return f"{q} {product}".strip()
    if style == 1 and n <= 12:
        return _pick(QTY_X).format(n=n, p=product)
    if style == 2:
        return f"{n} {product}"
    return f"{q} de {product}" if "de " not in product else f"{q} {product}"


def _combo_order() -> Tuple[str, str, str]:
    """Returns (message, productos_en_mensaje, notas)."""
    p1 = _pick(PIZZA_FORMS + TYPO_PIZZA)
    p2 = _pick(DRINK_FORMS + TYPO_DRINK)
    n1 = _pick([1, 1, 2, 2, 3])
    n2 = _pick([1, 1, 2])
    a = _qty_phrase(n1, p1)
    b = _qty_phrase(n2, p2)
    sep = _pick(SEP)
    msg = f"{_pick(PREFIX_ORDER)}{a}{sep}{b}{_pick(SUFFIX)}".strip()
    return msg, "si", "pedido multi-item menu real"


def _cat_count(rows: List[Record], categoria: str) -> int:
    return sum(1 for r in rows if r["categoria"] == categoria)


def _fill_category(
    gen_fn,
    seen: Set[str],
    rows: List[Record],
    categoria: str,
    target: int,
) -> None:
    """Run category generator once (internal loops handle stall limits)."""
    gen_fn(seen, rows, target)


def _emit(
    seen: Set[str],
    rows: List[Record],
    msg: str,
    categoria: str,
    sub: str,
    intent: str,
    prod: str,
    notas: str,
) -> bool:
    key = re.sub(r"\s+", " ", msg.strip().lower())
    if not key or key in seen or len(key) < 1:
        return False
    seen.add(key)
    rows.append(
        {
            "categoria": categoria,
            "subcategoria": sub,
            "mensaje": msg.strip(),
            "intencion_esperada": intent,
            "productos_en_mensaje": prod,
            "notas": notas,
        }
    )
    return True


def _gen_onboarding(seen: Set[str], rows: List[Record], n: int) -> None:
    templates: List[Tuple[str, str, str, str, str]] = []
    for intent, phrase in (
        MENU_INTENTS
        + PEDIDO_INTENTS
        + RESERVAR_INTENTS
        + INICIO_INTENTS
        + CANCELAR_INTENTS
    ):
        templates.append(("A_onboarding", intent, phrase, intent, "no", "comando/intencion global"))
    saludos = [
        ("hola", "saludo", "no"),
        ("buenas", "saludo", "no"),
        ("buenos dias", "saludo", "no"),
        ("hey que tal", "saludo", "no"),
        ("buenas tardes", "saludo", "no"),
    ]
    for s, intent, prod in saludos:
        templates.append(("A_onboarding", "saludo", s, intent, prod, "saludo puro"))
    fillers = ["", "porfa ", "please ", "oye ", "buenas ", "👋 ", "??? "]
    tails = ["", " porfa", " plis", " gracias", " !!", " ???"]
    stall = 0
    while _cat_count(rows, "A_onboarding") < n and stall < n * 30:
        _cat, sub, phrase, exp, prod, note = random.choice(templates)
        msg = f"{_pick(fillers)}{phrase}{_pick(tails)}"
        if random.random() < 0.15:
            msg += f" {random.randint(1, 999)}"
        stall = 0 if _emit(seen, rows, msg, "A_onboarding", sub, exp, prod, note) else stall + 1


def _gen_pedidos(seen: Set[str], rows: List[Record], n: int) -> None:
    stall = 0
    while _cat_count(rows, "B_pedido_nl") < n and stall < n * 25:
        if random.random() < 0.15:
            msg = _pick(CATEGORY_PHRASES)
            prod = "parcial"
            note = "solo categoria sin nombre exacto"
        else:
            msg, prod, note = _combo_order()
            if random.random() < 0.3:
                msg = _qty_phrase(_pick([1, 2, 3, 4]), _pick(PIZZA_FORMS + TYPO_PIZZA))
            if random.random() < 0.2:
                msg = _qty_phrase(_pick([1, 2]), _pick(DRINK_FORMS))
        full = f"{_pick(PREFIX_ORDER)}{msg}{_pick(SUFFIX)}"
        stall = (
            0
            if _emit(
                seen,
                rows,
                full,
                "B_pedido_nl",
                "pedido_producto",
                "pedido_con_productos",
                prod,
                note,
            )
            else stall + 1
        )


def _gen_carrito(seen: Set[str], rows: List[Record], n: int) -> None:
    stall = 0
    while _cat_count(rows, "C_carrito") < n and stall < n * 25:
        before = _cat_count(rows, "C_carrito")
        _gen_carrito_one(seen, rows)
        stall = 0 if _cat_count(rows, "C_carrito") > before else stall + 1


def _gen_carrito_one(seen: Set[str], rows: List[Record]) -> None:
    verbs = [
        ("agrega", "agregar", "modificar_carrito"),
        ("agregame", "agregar", "modificar_carrito"),
        ("quita", "quitar", "modificar_carrito"),
        ("quitame la", "quitar", "modificar_carrito"),
        ("sin", "quitar", "modificar_carrito"),
        ("cambia", "cambiar", "modificar_carrito"),
        ("reemplaza", "reemplazar", "modificar_carrito"),
        ("otra", "mas", "modificar_carrito"),
        ("ya no quiero", "quitar", "modificar_carrito"),
    ]
    targets = PIZZA_FORMS + DRINK_FORMS + ["cocacola", "hawaiana", "la pizza", "la bebida"]
    confirms = [
        ("si", "confirmar", "confirmacion pedido"),
        ("sí", "confirmar", "confirmacion pedido"),
        ("ok", "confirmar", "confirmacion pedido"),
        ("dale", "confirmar", "confirmacion pedido"),
        ("no", "rechazar", "rechazo modificar"),
        ("nop", "rechazar", "rechazo modificar"),
        ("mejor no", "rechazar", "rechazo modificar"),
    ]
    if random.random() < 0.35:
        cmsg, intent, sub = _pick(confirms)
        _emit(seen, rows, cmsg, "C_carrito", sub, intent, "no", "flujo confirmacion")
    else:
        v, sub, intent = _pick(verbs)
        t = _pick(targets)
        msg = f"{v} {t}"
        if v == "cambia":
            msg = f"cambia {t} por {_pick(targets)}"
        _emit(
            seen,
            rows,
            msg,
            "C_carrito",
            sub,
            intent,
            "parcial",
            "operacion carrito",
        )


def _gen_reserva(seen: Set[str], rows: List[Record], n: int) -> None:
    personas = ["2", "3", "4", "5", "6", "8", "10", "4 personas", "6 personas", "dos", "tres"]
    fechas = [
        "hoy",
        "mañana",
        "pasado mañana",
        "el viernes",
        "el sabado",
        "15/06/2026",
        "20-03-2026",
        "28 de marzo",
    ]
    horas = ["8pm", "20:00", "8:30", "nueve", "21 hrs", "7 de la noche", "mediodia"]
    stall = 0
    while _cat_count(rows, "D_reserva") < n and stall < n * 25:
        p = _pick(personas)
        f = _pick(fechas)
        h = _pick(horas)
        kind = random.randint(0, 4)
        if kind == 0:
            msg = f"reservar mesa para {p}"
            intent = "reservar"
        elif kind == 1:
            msg = f"{p} personas el {f}"
            intent = "dato_reserva"
        elif kind == 2:
            msg = f"para las {h}"
            intent = "dato_reserva"
        elif kind == 3:
            msg = f"reserva {f} a las {h} para {p}"
            intent = "dato_reserva"
        else:
            msg = _pick([t[1] for t in RESERVAR_INTENTS])
            intent = "reservar"
        stall = (
            0
            if _emit(seen, rows, msg, "D_reserva", "reserva", intent, "no", "flujo reserva")
            else stall + 1
        )


def _gen_entrega(seen: Set[str], rows: List[Record], n: int) -> None:
    calles = ["Reforma", "Juarez", "Hidalgo", "5 de Mayo", "Insurgentes", "Morelos"]
    cols = ["Centro", "Norte", "Sur", "centro", "col del valle"]
    dom = ["domicilio", "a domicilio", "para mi casa", "envio a casa", "1", "opcion 1"]
    recoger = ["recoger", "pasar por el", "pickup", "2", "en tienda", "paso a recoger"]
    nombres = ["Juan", "Maria", "Pedro", "Ana", "Luis", "Sofia", "Carlos", "Lucia"]
    stall = 0
    while _cat_count(rows, "E_entrega") < n and stall < n * 30:
        k = random.randint(0, 5)
        if k == 0:
            msg = _pick(dom)
            sub = "tipo_entrega"
        elif k == 1:
            msg = _pick(recoger)
            sub = "tipo_entrega"
        elif k == 2:
            msg = f"Calle {_pick(calles)} {_pick(range(1, 200))} col {_pick(cols)}"
            sub = "direccion"
        elif k == 3:
            msg = _pick(
                [
                    "la de siempre",
                    "si uso mi direccion guardada",
                    "misma direccion de siempre porfa",
                ]
            )
            sub = "direccion"
        elif k == 4:
            msg = f"me llamo {_pick(nombres)} {_pick(nombres)}"
            sub = "nombre"
        else:
            msg = f"{_pick(['tel', 'cel'])} {_pick(range(1000000, 9999999))}"
            sub = "telefono"
        stall = (
            0
            if _emit(seen, rows, msg, "E_entrega", sub, "datos_entrega", "no", "captura entrega")
            else stall + 1
        )


def _gen_mezclas(seen: Set[str], rows: List[Record], n: int) -> None:
    stall = 0
    while _cat_count(rows, "F_mezclas") < n and stall < n * 25:
        order, _, _ = _combo_order()
        templates = [
            f"hola {order}",
            f"menu y {order}",
            f"ver carta y {order}",
            f"{order} y tambien quiero reservar",
            f"reservar mesa y {order}",
            f"pedido: {order}",
            f"buenas, {_pick(PIZZA_FORMS)}",
            f"inicio ... no mejor {order}",
            f"cancelar ... es broma, {order}",
        ]
        msg = _pick(templates)
        intent = "pedido_con_productos" if any(
            x in msg.lower() for x in ("hawaiana", "coca", "pizza", "2 ", "3 ")
        ) else "ambiguo"
        prod = "si" if intent == "pedido_con_productos" else "parcial"
        stall = (
            0
            if _emit(seen, rows, msg, "F_mezclas", "combinada", intent, prod, "mezcla intenciones")
            else stall + 1
        )


def _gen_ruido(seen: Set[str], rows: List[Record], n: int) -> None:
    bases = [
        ("?", "ruido", "mensaje vacio"),
        ("...", "ruido", "ellipsis"),
        ("jajaja", "ruido", "risa"),
        ("ok", "ambiguo", "monosilabo"),
        ("a que hora abren", "ruido", "fuera de alcance"),
        ("tienen baño", "ruido", "fuera de alcance"),
        ("busco trabajo", "ruido", "fuera de alcance"),
        ("do you have pizza", "ruido", "spanglish"),
        ("menu pls", "menu", "spanglish menu"),
        ("asdf", "ruido", "gibberish"),
        ("cuanto tardan", "ruido", "logistica"),
        ("aceptan tarjeta", "ruido", "pago"),
        ("gracias", "saludo", "cierre"),
        ("perfecto", "confirmar", "confirmacion"),
        ("esta bien", "confirmar", "confirmacion"),
        ("👍", "ruido", "emoji"),
        ("🍕", "ruido", "emoji"),
        ("hola?", "ambiguo", "saludo duda"),
        ("?", "ruido", "signo"),
    ]
    extras = ["", " !!", " oye", " plis", " no se", " ayuda", " ???", " jaja"]
    nums = ["", " 1", " 2", " 5", " 12"]
    stall = 0
    while _cat_count(rows, "G_ruido") < n and stall < n * 30:
        msg, intent, note = _pick(bases)
        text = (msg + _pick(extras) + _pick(nums)).strip() or msg
        stall = (
            0
            if _emit(seen, rows, text, "G_ruido", "ruido_realista", intent, "no", note)
            else stall + 1
        )


def _gen_adversarial(seen: Set[str], rows: List[Record], n: int) -> None:
    fake_products = [
        "10 pizzas pepperoni",
        "sushi roll",
        "tacos al pastor",
        "lasagna",
        "100 hawaianas",
        "cero cocacolas",
        "-2 pizzas",
        "burger doble",
        "ensalada cesar",
        "latte grande",
        "wings picosas",
    ]
    qtys = ["", "2 ", "5 ", "una ", "docena de "]
    stall = 0
    while _cat_count(rows, "H_adversarial") < n and stall < n * 25:
        k = random.randint(0, 3)
        if k == 0:
            msg = f"{_pick(qtys)}{_pick(fake_products)}"
            note = "producto no en menu"
            prod = "parcial"
            intent = "pedido_con_productos"
        elif k == 1:
            msg = f"si y no {random.randint(1, 99)} quiero todo y nada"
            note = "contradiccion"
            prod = "no"
            intent = "ambiguo"
        elif k == 2:
            msg = _pick(["qwerty pizza", "zzzz", "123456789", ";;;", "asdf qwerty"])
            note = "gibberish"
            prod = "no"
            intent = "ruido"
        else:
            msg = f"{_pick(qtys)}{_pick(fake_products)} y {_pick(qtys)}{_pick(fake_products)}"
            note = "multi fake"
            prod = "parcial"
            intent = "pedido_con_productos"
        stall = (
            0
            if _emit(seen, rows, msg, "H_adversarial", "adversarial", intent, prod, note)
            else stall + 1
        )


def generate() -> List[Record]:
    seen: Set[str] = set()
    rows: List[Record] = []
    quotas = {
        "A_onboarding": 360,
        "B_pedido_nl": 1280,
        "C_carrito": 430,
        "D_reserva": 290,
        "E_entrega": 230,
        "F_mezclas": 240,
        "G_ruido": 200,
        "H_adversarial": 270,
    }
    gens = {
        "A_onboarding": _gen_onboarding,
        "B_pedido_nl": _gen_pedidos,
        "C_carrito": _gen_carrito,
        "D_reserva": _gen_reserva,
        "E_entrega": _gen_entrega,
        "F_mezclas": _gen_mezclas,
        "G_ruido": _gen_ruido,
        "H_adversarial": _gen_adversarial,
    }
    for cat, cap in quotas.items():
        _fill_category(gens[cat], seen, rows, cat, cap)

    return rows


def summary_table(rows: List[Record]) -> str:
    total = len(rows)
    by_cat: Dict[str, int] = {}
    by_intent: Dict[str, int] = {}
    for r in rows:
        by_cat[r["categoria"]] = by_cat.get(r["categoria"], 0) + 1
        by_intent[r["intencion_esperada"]] = by_intent.get(r["intencion_esperada"], 0) + 1

    lines = [
        "# Resumen cobertura corpus (~95% tráfico esperado)",
        f"Total líneas: {total}",
        "",
        "## Por categoría",
        "| Categoría | Líneas | % | Rol en cobertura |",
        "|-----------|--------|---|------------------|",
    ]
    labels = {
        "A_onboarding": "Navegación / comandos / saludos",
        "B_pedido_nl": "Pedidos lenguaje natural",
        "C_carrito": "Carrito y confirmación",
        "D_reserva": "Reserva de mesa",
        "E_entrega": "Domicilio / dirección / nombre",
        "F_mezclas": "Mensajes mixtos críticos",
        "G_ruido": "Ruido y fuera de alcance",
        "H_adversarial": "Adversarial / no menú",
    }
    for cat in sorted(by_cat.keys()):
        n = by_cat[cat]
        pct = 100.0 * n / total
        lines.append(f"| {cat} | {n} | {pct:.1f}% | {labels.get(cat, '')} |")
    lines.extend(["", "## Por intención esperada (top)", ""])
    for intent, n in sorted(by_intent.items(), key=lambda x: -x[1])[:15]:
        lines.append(f"- {intent}: {n} ({100*n/total:.1f}%)")
    return "\n".join(lines)


GAPS = """# Top 30 huecos (~5% no cubierto)

1. Audio de voz mal transcrito con palabras inventadas
2. Imagen/foto del menú sin texto
3. Pedidos en idioma indígena o portugués mezclado
4. Referencias a promos del mes no configuradas en flujo
5. Pedido para fecha futura específica (navidad, cumple)
6. Split bill / pagar separado entre personas
7. Alergias y restricciones médicas largas
8. Quejas formales / pedir gerente
9. Propinas en el mensaje de pedido
10. Cupones y códigos de descuento
11. Pedido B2B (oficina, 50 personas)
12. Coordenadas GPS en lugar de dirección
13. Ubicación compartida de WhatsApp (lat/long)
14. Reenvío de mensaje de otro contacto
15. Catálogo PDF adjunto referenciado
16. Menú de competencia mencionado
17. Pedidos de desayuno si el local no abre
18. Solicitud de factura CFDI con RFC
19. Cambio de método de pago mid-flujo
20. Multi-sucursal ("sucursal norte")
21. Pedido programado exacto al minuto
22. Modificar pedido ya entregado
23. Estado de pedido en ruta (tracking)
24. Chat interno entre empleados por error
25. Stickers animados sin texto util
26. Plantillas WhatsApp Business del cliente
27. Mensajes de bot de otro negocio copiados
28. Unicode raro / caracteres RTL
29. Pedido en dialecto muy local no listado
30. Conversación multi-turno referenciando "lo de arriba"

**Detección en logs:** buscar en `client_messages_log` respuestas fallback repetidas,
`Aún no tengo productos`, `No logré entender`, o mismos `wa_id` con 3+ reformulaciones seguidas.
"""


PARSER_PRIORITIES = """# 15 cambios sugeridos (parser.py / GLOBAL_COMMAND_INTENTS)

1. Filtrar segmentos `unknown` que son solo frases de intención ("quiero comer", "tomar") — no tratarlos como producto.
2. Expandir `ORDER_INTENT_NON_PRODUCT` en señal de cantidad para "tomar", "comer", "ordenar".
3. Sinónimo `tomar` → bebida solo si hay ítem bebida en menú y contexto de cantidad.
4. Boost fuzzy `hawaina` / `hawaiiana` → Hawaiana (ya parcial; reforzar en typos).
5. `refresco` / `soda` → cocacola cuando una sola bebida en menú.
6. Frase compuesta "quiero comer algo" → intención pedido sin productos.
7. "menu" dentro de pedido largo → no cortar flujo si `has_products`.
8. Reserva: reconocer "para el 15" sin mes sin perder como fecha.
9. Confirmación: mapear "esta bien", "ok gracias", "va" → confirmar.
10. Carrito: "sin cebolla" como nota, no producto (notas en parser).
11. Cantidad "docena" solo con productos contables del menú.
12. Ignorar segmentos de 1 palabra en NOISE_WORDS al armar unknown.
13. Prefijo "pedido:" como etiqueta admin de pedido (ya existe; documentar).
14. Categoría "pizza" → default Hawaiana si es única pizza disponible.
15. Log interno opcional `intent` en parser audit sin mostrar al usuario.
"""


def main() -> None:
    rows = generate()
    if len(rows) < TARGET:
        print(f"Warning: only {len(rows)} unique lines (target {TARGET})")

    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(r["mensaje"] + "\n")

    fieldnames = [
        "id",
        "categoria",
        "subcategoria",
        "mensaje",
        "intencion_esperada",
        "productos_en_mensaje",
        "notas",
    ]
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for i, r in enumerate(rows, start=1):
            w.writerow({"id": i, **r})

    summary_path = ROOT / "data" / "parser_corpus_95_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_table(rows))
        f.write("\n\n")
        f.write(GAPS)
        f.write("\n\n")
        f.write(PARSER_PRIORITIES)

    print(summary_table(rows))
    print(f"\nWrote {len(rows)} lines -> {OUT_TXT}")
    print(f"Wrote CSV -> {OUT_CSV}")
    print(f"Summary -> {summary_path}")


if __name__ == "__main__":
    main()
