from __future__ import annotations

from typing import Any, Dict, List

from app.integrations.google_sheets import GoogleSheetsClient


class MenuService:
    def __init__(self, sheets: GoogleSheetsClient) -> None:
        self.sheets = sheets

    def get_available_menu(self) -> List[Dict[str, Any]]:
        return [
            item for item in self.sheets.get_menu() if item.get("disponible", True)
        ]

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
