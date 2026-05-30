"""Google Sheets integration with graceful fallback demo data."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEMO_MENU = [
    {
        "id": "1",
        "nombre": "Pizza Hawaiana",
        "precio": 12.5,
        "categoria": "Pizzas",
        "disponible": True,
    },
    {
        "id": "2",
        "nombre": "Pizza Margarita",
        "precio": 11.0,
        "categoria": "Pizzas",
        "disponible": True,
    },
    {
        "id": "3",
        "nombre": "Hamburguesa Clásica",
        "precio": 9.5,
        "categoria": "Hamburguesas",
        "disponible": True,
    },
    {
        "id": "4",
        "nombre": "Coca Cola",
        "precio": 2.5,
        "categoria": "Bebidas",
        "disponible": True,
    },
    {
        "id": "5",
        "nombre": "Agua Mineral",
        "precio": 1.5,
        "categoria": "Bebidas",
        "disponible": True,
    },
    {
        "id": "6",
        "nombre": "Ensalada César",
        "precio": 8.0,
        "categoria": "Ensaladas",
        "disponible": True,
    },
]

SHEET_HEADERS = {
    "MENU": ["id", "nombre", "precio", "categoria", "disponible"],
    "USERS": ["wa_id", "name", "last_seen"],
    "ORDERS": ["order_id", "wa_id", "items", "total", "status", "timestamp"],
    "RESERVATIONS": [
        "reservation_id",
        "wa_id",
        "personas",
        "fecha",
        "hora",
        "status",
    ],
}


class GoogleSheetsClient:
    def __init__(self, credentials_path: str, spreadsheet_id: str) -> None:
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self._client = None
        self._spreadsheet = None
        self._connected = False
        self._connect()

    def _connect(self) -> None:
        if not self.spreadsheet_id:
            logger.warning("GOOGLE_SPREADSHEET_ID not set. Using demo data.")
            return
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=scopes,
            )
            self._client = gspread.authorize(credentials)
            self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)
            self._connected = True
            self._ensure_worksheets()
        except Exception as exc:
            logger.warning("Google Sheets unavailable (%s). Using demo data.", exc)
            self._connected = False

    def _ensure_worksheets(self) -> None:
        if not self._spreadsheet:
            return
        existing = {ws.title.upper(): ws for ws in self._spreadsheet.worksheets()}
        for sheet_name, headers in SHEET_HEADERS.items():
            if sheet_name not in existing:
                worksheet = self._spreadsheet.add_worksheet(
                    title=sheet_name,
                    rows=1000,
                    cols=len(headers),
                )
                worksheet.append_row(headers)
            else:
                worksheet = existing[sheet_name]
                current = worksheet.row_values(1)
                if not current:
                    worksheet.append_row(headers)

    def _get_sheet(self, name: str):
        if not self._connected or not self._spreadsheet:
            return None
        return self._spreadsheet.worksheet(name)

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "si", "sí", "yes", "y"}

    def get_menu(self) -> List[Dict[str, Any]]:
        sheet = self._get_sheet("MENU")
        if not sheet:
            return DEMO_MENU

        rows = sheet.get_all_records()
        menu = []
        for row in rows:
            if not row.get("nombre"):
                continue
            menu.append(
                {
                    "id": str(row.get("id", "")),
                    "nombre": str(row.get("nombre", "")).strip(),
                    "precio": float(row.get("precio", 0) or 0),
                    "categoria": str(row.get("categoria", "")).strip(),
                    "disponible": self._parse_bool(row.get("disponible", True)),
                }
            )
        return menu or DEMO_MENU

    def upsert_user(self, wa_id: str, name: str = "") -> None:
        sheet = self._get_sheet("USERS")
        if not sheet:
            return

        rows = sheet.get_all_records()
        now = datetime.utcnow().isoformat()
        for idx, row in enumerate(rows, start=2):
            if str(row.get("wa_id")) == wa_id:
                sheet.update(f"B{idx}:C{idx}", [[name or row.get("name", ""), now]])
                return
        sheet.append_row([wa_id, name, now])

    def create_order(
        self,
        wa_id: str,
        items: List[Dict[str, Any]],
        total: float,
        status: str = "pending",
    ) -> str:
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        payload = {
            "order_id": order_id,
            "wa_id": wa_id,
            "items": items,
            "total": total,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        sheet = self._get_sheet("ORDERS")
        if sheet:
            sheet.append_row(
                [
                    order_id,
                    wa_id,
                    json.dumps(items, ensure_ascii=False),
                    total,
                    status,
                    payload["timestamp"],
                ]
            )
        return order_id

    def create_reservation(
        self,
        wa_id: str,
        personas: int,
        fecha: str,
        hora: str,
        status: str = "confirmed",
    ) -> str:
        reservation_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
        sheet = self._get_sheet("RESERVATIONS")
        if sheet:
            sheet.append_row(
                [reservation_id, wa_id, personas, fecha, hora, status]
            )
        return reservation_id
