from __future__ import annotations

from typing import Any, Dict, List

from app.integrations.google_sheets import GoogleSheetsClient


class MenuService:
    def __init__(self, sheets: GoogleSheetsClient) -> None:
        self.sheets = sheets

    def _fetch_available_menu(self) -> List[Dict[str, Any]]:
        return [
            item for item in self.sheets.get_menu() if item.get("disponible", True)
        ]

    def get_available_menu(self) -> List[Dict[str, Any]]:
        try:
            from flask import g, has_request_context
        except ImportError:
            return self._fetch_available_menu()

        if not has_request_context():
            return self._fetch_available_menu()

        cached = getattr(g, "_available_menu_cache", None)
        if cached is not None:
            return cached

        menu = self._fetch_available_menu()
        g._available_menu_cache = menu
        return menu

    def format_menu(self) -> str:
        menu = self.get_available_menu()
        if not menu:
            return "Por el momento no tenemos platos disponibles. Intenta más tarde."

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in menu:
            category = item.get("categoria") or "General"
            grouped.setdefault(category, []).append(item)

        lines = ["*Nuestro menú*\n"]
        for category, items in grouped.items():
            lines.append(f"*{category}*")
            for item in items:
                lines.append(f"• {item['nombre']} — ${item['precio']:.2f}")
            lines.append("")

        return "\n".join(lines).strip()

    def save_item(
        self,
        item_id: str,
        nombre: str,
        precio: float,
        categoria: str,
        disponible: bool = True,
    ) -> bool:
        return self.sheets.upsert_menu_item(
            item_id, nombre, precio, categoria, disponible
        )

    def remove_item(self, item_id: str, *, hard: bool = False) -> bool:
        return self.sheets.remove_menu_item(item_id, hard=hard)

    def set_availability(self, item_id: str, disponible: bool) -> bool:
        return self.sheets.set_menu_item_availability(item_id, disponible)
