"""Genera 2000 frases cotidianas de pedido por WhatsApp (español, una línea cada una)."""
from __future__ import annotations

import random
import re
from pathlib import Path

random.seed(20260303)

# Productos y formas habituales en mensajes reales (pizzería / fast food / mixto)
PRODUCTS: list[tuple[str, str]] = [
    ("pizza hawaiana", "pizza"),
    ("pizza margarita", "pizza"),
    ("pizza de jamón y queso", "pizza de"),
    ("pizza mexicana", "pizza"),
    ("pizza ranchera", "pizza"),
    ("pizza pepperoni", "pizza"),
    ("hamburguesa clásica", "hamburguesa"),
    ("hamburguesa mega", "hamburguesa"),
    ("hamburguesa doble carne", "hamburguesa"),
    ("hamburguesa doble pollo", "hamburguesa"),
    ("hamburguesa con queso", "hamburguesa"),
    ("papas fritas", ""),
    ("papas grandes", ""),
    ("ensalada césar", "ensalada"),
    ("ensalada mixta", "ensalada"),
    ("coca cola", ""),
    ("coca cola sin azúcar", ""),
    ("agua mineral", ""),
    ("agua embotellada", ""),
    ("limonada natural", ""),
    ("jugo de naranja", ""),
    ("café americano", ""),
    ("té helado", ""),
    ("alitas de pollo", ""),
    ("nuggets de pollo", ""),
    ("hot dog sencillo", ""),
    ("torta de milanesa", ""),
    ("quesadilla de queso", ""),
    ("tacos al pastor", ""),
    ("burrito de frijol", ""),
    ("orden de aros de cebolla", ""),
]

QTY_NUMBERS = [1, 2, 2, 3, 3, 4, 5, 6, 8, 10, 12]

QTY_WORDS: dict[int, list[str]] = {
    1: ["una", "un", "1"],
    2: ["dos", "2", "un par de"],
    3: ["tres", "3"],
    4: ["cuatro", "4"],
    5: ["cinco", "5"],
    6: ["seis", "6"],
    8: ["ocho", "8"],
    10: ["diez", "10"],
    12: ["doce", "12", "una docena de"],
}

PREFIXES = [
    "",
    "hola ",
    "hola buenas ",
    "buenas tardes ",
    "buenas noches ",
    "buenos días ",
    "buen día ",
    "hey ",
    "qué tal ",
    "oye ",
    "disculpa ",
    "por favor ",
    "porfa ",
    "quisiera ",
    "quiero ",
    "me gustaría ",
    "necesito ",
    "dame ",
    "deme ",
    "me pones ",
    "me traes ",
    "tráeme ",
    "ponme ",
    "voy a querer ",
    "te encargo ",
    "me das ",
    "me mandas ",
    "para pedir ",
]

SUFFIXES = [
    "",
    " porfa",
    " por favor",
    " plis",
    " gracias",
    " please",
    " para llevar",
    " para aquí",
    " para comer ahí",
    " nomás",
    " nada más",
]

SEPARATORS = [" y ", ", ", " + ", " | ", "; ", " luego ", " además ", " aparte ", " también "]

# Typos leves que sí aparecen en WhatsApp real (no caricatura)
TYPO_MAP = {
    "hamburguesa": "hamburguesa",
    "clásica": "clasica",
    "jamón": "jamon",
    "césar": "cesar",
    "pizza": "pizza",
    "coca cola": "coca cola",
}

MILD_TYPOS = {
    "hamburguesa": ["hamburgesa", "hamburguesa"],
    "pizza": ["piza", "pizza"],
    "coca cola": ["cocacola", "coca cola"],
    "clásica": ["clasica", "clásica"],
    "jamón": ["jamon", "jamón"],
    "césar": ["cesar", "césar"],
}

MENU_PHRASES = [
    "menú",
    "menú porfa",
    "la carta",
    "qué tienen",
    "qué tienen de comer",
    "qué hay",
    "ver el menú",
    "pásame el menú",
    "mostrar carta",
    "lista de precios",
]

CART_PHRASES_TEMPLATES = [
    "quítame {item}",
    "quita {item}",
    "sácame {item}",
    "ya no quiero {item}",
    "cambia {old} por {new}",
    "en vez de {old} pon {new}",
    "agrega {item}",
    "súmale {item}",
]

# Semillas tomadas de mensajes muy frecuentes en pedidos por chat
SEED_PHRASES = [
    "hola, quiero 2 pizzas hawaianas y 1 coca cola",
    "buenas, una hamburguesa clásica con papas fritas",
    "dame 3 tacos al pastor por favor",
    "2 hamburguesas mega y 2 aguas mineral",
    "una pizza margarita, gracias",
    "tres cocas cola y una ensalada césar",
    "me pones 2 burritos de frijol y 1 limonada natural",
    "un par de hawaianas y una coca",
    "quisiera 2 ensaladas y 1 café americano",
    "2x pizza de jamón y queso",
    "x2 agua mineral",
    "pizza hawaiana y coca cola",
    "hamburguesa clásica y papas",
    "menú porfa",
    "qué tienen de bebidas",
    "quítame una coca cola",
    "cambia la margarita por hawaiana",
    "para llevar: 2 mega y 1 papas fritas",
    "bueno, 2 hawaianas y tres cocas",
    "me das una ranchera y dos papas grandes",
    "pedido: 2 hawaiana, 1 coca, 1 agua",
    "dos pizzas margarita, una hawaiana",
    "tres hamburguesas y una limonada",
    "solo una ensalada césar",
    "4 alitas y 2 cocas porfa",
]


def normalize_line(text: str) -> str:
    return " ".join(text.replace("\n", " ").split()).strip()


def maybe_typo(text: str) -> str:
    low = text.lower()
    if random.random() > 0.22:
        return low
    for key, options in MILD_TYPOS.items():
        if key in low:
            return low.replace(key, random.choice(options), 1)
    return low


def qty_fragment(n: int) -> str:
    if n in QTY_WORDS and random.random() < 0.58:
        return random.choice(QTY_WORDS[n])
    roll = random.random()
    if roll < 0.18:
        return f"{n}x"
    if roll < 0.28:
        return f"x{n}"
    return str(n)


def format_item() -> str:
    n = random.choice(QTY_NUMBERS)
    product, category = random.choice(PRODUCTS)
    product = maybe_typo(product)
    qty = qty_fragment(n)
    if category and random.random() < 0.32:
        return f"{qty} {category} {product}".strip()
    return f"{qty} {product}".strip()


def format_multi(count: int | None = None) -> str:
    parts = count or random.randint(2, 4)
    sep = random.choice(SEPARATORS)
    return sep.join(format_item() for _ in range(parts))


def format_order() -> str:
    prefix = random.choice(PREFIXES)
    suffix = random.choice(SUFFIXES)
    body = format_multi() if random.random() < 0.82 else format_item()
    return normalize_line(f"{prefix}{body}{suffix}")


def format_whatsapp_inline_list() -> str:
    count = random.randint(2, 4)
    intro = random.choice(["", "pedido: ", "mi pedido: ", "anoto: "])
    items = [format_item() for _ in range(count)]
    joined = " | ".join(items) if random.random() < 0.5 else ", ".join(items)
    return normalize_line(f"{intro}{joined}")


def format_cart() -> str:
    old = format_item()
    new = format_item()
    tpl = random.choice(CART_PHRASES_TEMPLATES)
    if "{old}" in tpl and "{new}" in tpl:
        return tpl.format(old=old, new=new)
    return tpl.format(item=old)


def generate_pool(target: int = 2000) -> list[str]:
    seen: set[str] = set()
    phrases: list[str] = []

    for seed in SEED_PHRASES:
        line = normalize_line(seed)
        key = line.lower()
        if key not in seen:
            seen.add(key)
            phrases.append(line)

    generators = [
        (format_order, 0.72),
        (format_whatsapp_inline_list, 0.08),
        (lambda: format_multi(random.randint(2, 5)), 0.10),
        (format_item, 0.06),
        (lambda: random.choice(MENU_PHRASES), 0.02),
        (format_cart, 0.02),
    ]

    attempts = 0
    while len(phrases) < target and attempts < target * 20:
        attempts += 1
        roll = random.random()
        cumulative = 0.0
        chosen = format_order
        for gen, weight in generators:
            cumulative += weight
            if roll <= cumulative:
                chosen = gen
                break
        line = normalize_line(chosen() if callable(chosen) else str(chosen))
        if len(line) < 4:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        phrases.append(line)

    return phrases[:target]


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "data" / "parser_stress_2000_cotidianas.txt"
    phrases = generate_pool(2000)
    out.write_text("\n".join(phrases) + "\n", encoding="utf-8")

    multi = sum(1 for p in phrases if re.search(r"[,+|;]| y |luego|además|aparte", p))
    greeting = sum(
        1
        for p in phrases
        if re.match(r"^(hola|buenas|buenos|hey|qué tal|oye|buen día)", p, re.I)
    )
    print(f"Archivo: {out}")
    print(f"Líneas: {len(phrases)}")
    print(f"Con varios ítems: {multi}")
    print(f"Con saludo: {greeting}")
    print(f"Menú/carta: {sum(1 for p in phrases if re.search(r'menú|carta|qué tienen|qué hay', p, re.I))}")
    print(f"Carrito (quitar/cambiar/agregar): {sum(1 for p in phrases if re.search(r'quita|quítame|saca|sácame|cambia|agrega|en vez', p, re.I))}")


if __name__ == "__main__":
    main()
