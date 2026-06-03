from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.integrations.google_sheets import GoogleSheetsClient

_MENU_CACHE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "menu_cache.json"
)


class MenuService:
    def __init__(self, sheets: GoogleSheetsClient) -> None:
        self.sheets = sheets
        self._formatted_menu_cache: Optional[str] = None
        self._formatted_menu_mtime: float = -1.0

    @staticmethod
    def _menu_cache_mtime() -> float:
        if not _MENU_CACHE_PATH.exists():
            return 0.0
        return _MENU_CACHE_PATH.stat().st_mtime

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
        mtime = self._menu_cache_mtime()
        if self._formatted_menu_cache is not None and self._formatted_menu_mtime == mtime:
            return self._formatted_menu_cache

        menu = self.get_available_menu()
        if not menu:
            formatted = (
                "Por el momento no tenemos platos disponibles. Intenta más tarde."
            )
        else:
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

            formatted = "\n".join(lines).strip()

        self._formatted_menu_cache = formatted
        self._formatted_menu_mtime = mtime
        return formatted
