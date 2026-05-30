"""Natural-language order parser with cart operations."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


NUMBER_WORDS = {
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize(value: str) -> str:
    cleaned = _strip_accents(value.lower().strip())
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


class OrderParser:
    def __init__(self, menu_items: List[Dict[str, Any]]) -> None:
        self.menu_items = [item for item in menu_items if item.get("disponible", True)]
        self._catalog = self._build_catalog()

    def _build_catalog(self) -> List[Dict[str, Any]]:
        catalog = []
        for item in self.menu_items:
            name = item.get("nombre", "")
            catalog.append(
                {
                    "id": item.get("id"),
                    "nombre": name,
                    "precio": float(item.get("precio", 0)),
                    "categoria": item.get("categoria", ""),
                    "tokens": normalize(name).split(),
                    "normalized": normalize(name),
                }
            )
        return sorted(catalog, key=lambda entry: len(entry["normalized"]), reverse=True)

    def _match_product(self, fragment: str) -> Optional[Dict[str, Any]]:
        query = normalize(fragment)
        if not query:
            return None

        best: Optional[Dict[str, Any]] = None
        best_score = 0.0

        for item in self._catalog:
            if query == item["normalized"]:
                return item
            if query in item["normalized"] or item["normalized"] in query:
                score = 0.95
            else:
                score = SequenceMatcher(None, query, item["normalized"]).ratio()

            token_overlap = len(set(query.split()) & set(item["tokens"])) / max(
                len(set(query.split()) | set(item["tokens"])), 1
            )
            score = max(score, token_overlap)

            if score > best_score:
                best_score = score
                best = item

        return best if best_score >= 0.55 else None

    def _extract_quantity(self, text: str) -> Tuple[int, str]:
        cleaned = normalize(text)
        digit_match = re.match(r"^(\d+)\s+(.*)$", cleaned)
        if digit_match:
            return int(digit_match.group(1)), digit_match.group(2).strip()

        for word, qty in NUMBER_WORDS.items():
            pattern = rf"^{word}\s+(.*)$"
            match = re.match(pattern, cleaned)
            if match:
                return qty, match.group(1).strip()

        return 1, cleaned

    def _split_segments(self, text: str) -> List[str]:
        raw = text.lower().strip()
        raw = re.sub(r"\s+y\s+", ",", raw)
        raw = re.sub(r"\s+e\s+", ",", raw)
        raw = re.sub(r"\s+mas\s+", ",", raw)
        raw = re.sub(r"\s+también\s+", ",", raw)
        raw = re.sub(r"\s+tambien\s+", ",", raw)

        comma_parts = [part.strip() for part in raw.split(",") if part.strip()]
        if len(comma_parts) > 1:
            return [normalize(part) for part in comma_parts]

        normalized = normalize(text)
        if normalized:
            return [normalized]
        return []

    def parse_additions(self, text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        items: List[Dict[str, Any]] = []
        unknown: List[str] = []

        for segment in self._split_segments(text):
            qty, product_text = self._extract_quantity(segment)
            matched = self._match_product(product_text)
            if matched:
                items.append(
                    {
                        "product_id": matched["id"],
                        "product": matched["nombre"],
                        "qty": qty,
                        "unit_price": matched["precio"],
                        "subtotal": round(qty * matched["precio"], 2),
                    }
                )
            else:
                unknown.append(segment)

        return items, unknown

    def parse_remove(self, text: str) -> Tuple[List[str], List[str]]:
        cleaned = normalize(text)
        cleaned = re.sub(r"^(quita|quitar|elimina|eliminar|saca|sacar)\s+", "", cleaned)
        cleaned = cleaned.replace(" la ", " ").replace(" el ", " ").replace(" los ", " ")
        cleaned = cleaned.replace(" las ", " ")

        removed: List[str] = []
        unknown: List[str] = []

        for segment in self._split_segments(cleaned):
            matched = self._match_product(segment)
            if matched:
                removed.append(matched["nombre"])
            else:
                unknown.append(segment)

        return removed, unknown

    def parse_replace(self, text: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        cleaned = normalize(text)
        patterns = [
            r"cambia\s+(.+?)\s+por\s+(.+)",
            r"reemplaza\s+(.+?)\s+por\s+(.+)",
            r"cambiar\s+(.+?)\s+por\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned)
            if not match:
                continue
            old_fragment, new_fragment = match.group(1).strip(), match.group(2).strip()
            old_item = self._match_product(old_fragment)
            new_item = self._match_product(new_fragment)
            if old_item and new_item:
                return old_item["nombre"], new_item["nombre"], []
            unknown = []
            if not old_item:
                unknown.append(old_fragment)
            if not new_item:
                unknown.append(new_fragment)
            return None, None, unknown
        return None, None, []

    def apply_message(
        self,
        text: str,
        current_cart: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        cart = [dict(item) for item in (current_cart or [])]
        notes: List[str] = []
        unknown: List[str] = []
        cleaned = normalize(text)

        if re.search(r"\b(quita|quitar|elimina|eliminar|saca|sacar)\b", cleaned):
            removed, unknown_remove = self.parse_remove(text)
            unknown.extend(unknown_remove)
            if removed:
                cart = [item for item in cart if item["product"] not in removed]
                notes.append(f"Eliminé: {', '.join(removed)}.")
            return {"items": cart, "notes": notes, "unknown": unknown}

        old_name, new_name, unknown_replace = self.parse_replace(text)
        unknown.extend(unknown_replace)
        if old_name and new_name:
            replaced = False
            for item in cart:
                if item["product"] == old_name:
                    new_match = self._match_product(new_name)
                    if new_match:
                        item["product_id"] = new_match["id"]
                        item["product"] = new_match["nombre"]
                        item["unit_price"] = new_match["precio"]
                        item["subtotal"] = round(item["qty"] * new_match["precio"], 2)
                        replaced = True
            if replaced:
                notes.append(f"Cambié {old_name} por {new_name}.")
            return {"items": cart, "notes": notes, "unknown": unknown}

        additions, unknown_add = self.parse_additions(text)
        unknown.extend(unknown_add)

        for addition in additions:
            found = False
            for item in cart:
                if item["product"] == addition["product"]:
                    item["qty"] += addition["qty"]
                    item["subtotal"] = round(item["qty"] * item["unit_price"], 2)
                    found = True
                    break
            if not found:
                cart.append(addition)

        return {"items": cart, "notes": notes, "unknown": unknown}

    @staticmethod
    def cart_total(items: List[Dict[str, Any]]) -> float:
        return round(sum(item.get("subtotal", 0) for item in items), 2)

    @staticmethod
    def format_cart(items: List[Dict[str, Any]]) -> str:
        if not items:
            return "Tu carrito está vacío."
        lines = []
        for item in items:
            lines.append(
                f"• {item['qty']} x {item['product']} — ${item['subtotal']:.2f}"
            )
        total = OrderParser.cart_total(items)
        lines.append(f"\n*Total: ${total:.2f}*")
        return "\n".join(lines)
