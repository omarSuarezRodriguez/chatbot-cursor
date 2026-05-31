"""Local simulation harness for multi-user flow testing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_ID, STATE_PERSIST_PATH
from app.core.flow_engine import FlowEngine
from app.core.state_manager import StateManager
from app.integrations.google_sheets import GoogleSheetsClient
from app.services.admin_service import AdminService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.reservation_service import ReservationService
from app.services.user_service import UserService


def run_scenario(wa_id: str, messages: list[str]) -> None:
    sheets = GoogleSheetsClient(
        GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_ID
    )
    state = StateManager(persist_path=None)
    menu_service = MenuService(sheets)
    order_service = OrderService(sheets, menu_service)
    engine = FlowEngine(
        state_manager=state,
        menu_service=menu_service,
        order_service=order_service,
        reservation_service=ReservationService(sheets),
        user_service=UserService(sheets),
        admin_service=AdminService(sheets, order_service),
    )

    print(f"\n=== User {wa_id} ===")
    for message in messages:
        print(f"\n> {message}")
        reply = engine.process_message(wa_id, message)
        print(reply[:500] + ("..." if len(reply) > 500 else ""))


if __name__ == "__main__":
    run_scenario(
        "user_a",
        [
            "hola",
            "pedido",
            "2 pizza hawaiana, 1 coca cola",
            "si",
        ],
    )
    run_scenario(
        "user_b",
        [
            "reservar",
            "4",
            "30/06/2026",
            "20:00",
            "si",
        ],
    )
    run_scenario(
        "user_a",
        [
            "quita la coca cola",
        ],
    )
