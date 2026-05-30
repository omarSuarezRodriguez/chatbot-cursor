from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.core.parser import OrderParser
from app.integrations.google_sheets import GoogleSheetsClient
from app.services.menu_service import MenuService


class OrderService:
    def __init__(self, sheets: GoogleSheetsClient, menu_service: MenuService) -> None:
        self.sheets = sheets
        self.menu_service = menu_service

    def _parser(self) -> OrderParser:
        return OrderParser(self.menu_service.get_available_menu())

    def parse_order_text(
        self,
        text: str,
        current_cart: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        return self._parser().apply_message(text, current_cart)

    def format_cart(self, items: List[Dict[str, Any]]) -> str:
        return OrderParser.format_cart(items)

    def cart_total(self, items: List[Dict[str, Any]]) -> float:
        return OrderParser.cart_total(items)

    def save_order(self, wa_id: str, items: List[Dict[str, Any]]) -> Tuple[str, float]:
        total = self.cart_total(items)
        order_id = self.sheets.create_order(wa_id=wa_id, items=items, total=total)
        return order_id, total
