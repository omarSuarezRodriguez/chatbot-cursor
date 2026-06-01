"""Google Sheets integration with graceful fallback demo data."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MENU_CACHE_TTL_SECONDS = 60
ORDERS_CACHE_TTL_SECONDS = 30

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
    "USERS": [
        "wa_id",
        "name",
        "address",
        "last_order_date",
        "last_order_json",
        "last_seen",
    ],
    "ORDERS": [
        "order_id",
        "wa_id",
        "items",
        "total",
        "status",
        "timestamp",
        "customer_name",
        "address",
        "delivery_type",
    ],
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
        self._demo_users: Dict[str, Dict[str, Any]] = {}
        self._demo_orders: List[Dict[str, Any]] = []
        self._cache_lock = threading.Lock()
        self._menu_cache: Optional[List[Dict[str, Any]]] = None
        self._menu_cache_expires: float = 0.0
        self._users_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._user_row_index: Optional[Dict[str, int]] = None
        self._orders_cache: Optional[List[Dict[str, Any]]] = None
        self._orders_cache_expires: float = 0.0
        self._worksheets: Dict[str, Any] = {}
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
            self._worksheets[sheet_name] = worksheet

    def _get_sheet(self, name: str):
        if not self._connected or not self._spreadsheet:
            return None
        if name in self._worksheets:
            return self._worksheets[name]
        worksheet = self._spreadsheet.worksheet(name)
        self._worksheets[name] = worksheet
        return worksheet

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "si", "sí", "yes", "y"}

    def _invalidate_orders_cache(self) -> None:
        with self._cache_lock:
            self._orders_cache = None
            self._orders_cache_expires = 0.0

    def _fetch_menu_rows(self) -> List[Dict[str, Any]]:
        sheet = self._get_sheet("MENU")
        if not sheet:
            return []

        menu: List[Dict[str, Any]] = []
        for row in sheet.get_all_records():
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
        return menu

    def _user_from_row(self, wa_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
        last_order = row.get("last_order_json") or ""
        try:
            last_order_items = json.loads(last_order) if last_order else []
        except json.JSONDecodeError:
            last_order_items = []
        return {
            "wa_id": wa_id,
            "name": str(row.get("name", "")).strip(),
            "address": str(row.get("address", "")).strip(),
            "last_order_date": str(row.get("last_order_date", "")).strip(),
            "last_order_items": last_order_items,
            "last_seen": str(row.get("last_seen", "")).strip(),
        }

    def _load_users_cache(self) -> Dict[str, Dict[str, Any]]:
        with self._cache_lock:
            if self._users_cache is not None:
                return self._users_cache

        sheet = self._get_sheet("USERS")
        users: Dict[str, Dict[str, Any]] = {}
        row_index: Dict[str, int] = {}
        if sheet:
            headers = SHEET_HEADERS["USERS"]
            for idx, raw in enumerate(sheet.get_all_values()[1:], start=2):
                if not raw or not str(raw[0]).strip():
                    continue
                padded = raw + [""] * (len(headers) - len(raw))
                row = dict(zip(headers, padded[: len(headers)]))
                wa_id = str(row.get("wa_id", "")).strip()
                if wa_id:
                    users[wa_id] = self._user_from_row(wa_id, row)
                    row_index[wa_id] = idx

        with self._cache_lock:
            self._users_cache = users
            self._user_row_index = row_index
            return self._users_cache

    def _resolve_user_row(self, sheet, wa_id: str) -> Optional[int]:
        row_idx = self._get_user_row(wa_id)
        if row_idx:
            return row_idx
        try:
            cell = sheet.find(wa_id, in_column=1)
        except Exception:
            return None
        if not cell:
            return None
        with self._cache_lock:
            if self._user_row_index is not None:
                self._user_row_index[wa_id] = cell.row
        return cell.row

    def _get_user_row(self, wa_id: str) -> Optional[int]:
        self._load_users_cache()
        with self._cache_lock:
            if not self._user_row_index:
                return None
            return self._user_row_index.get(wa_id)

    def _get_orders_records(self) -> List[Dict[str, Any]]:
        now = time.time()
        with self._cache_lock:
            if self._orders_cache is not None and now < self._orders_cache_expires:
                return self._orders_cache

        sheet = self._get_sheet("ORDERS")
        rows = sheet.get_all_records() if sheet else []

        with self._cache_lock:
            self._orders_cache = rows
            self._orders_cache_expires = now + ORDERS_CACHE_TTL_SECONDS
            return self._orders_cache

    def get_menu(self) -> List[Dict[str, Any]]:
        now = time.time()
        with self._cache_lock:
            if self._menu_cache is not None and now < self._menu_cache_expires:
                return list(self._menu_cache)

        menu = self._fetch_menu_rows()
        if not menu:
            return DEMO_MENU

        with self._cache_lock:
            self._menu_cache = menu
            self._menu_cache_expires = now + MENU_CACHE_TTL_SECONDS
        return list(menu)

    def get_user(self, wa_id: str) -> Dict[str, Any]:
        with self._cache_lock:
            if self._users_cache is not None:
                return dict(self._users_cache.get(wa_id, {}))

        sheet = self._get_sheet("USERS")
        if not sheet:
            return dict(self._demo_users.get(wa_id, {}))

        users = self._load_users_cache()
        return dict(users.get(wa_id, {}))

    def upsert_user(
        self,
        wa_id: str,
        name: str = "",
        address: str = "",
        last_order_items: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        existing = self.get_user(wa_id)
        merged_name = name or existing.get("name", "")
        merged_address = address or existing.get("address", "")
        merged_items = last_order_items if last_order_items is not None else existing.get(
            "last_order_items", []
        )
        last_order_date = existing.get("last_order_date", "")
        if last_order_items is not None:
            last_order_date = now

        sheet = self._get_sheet("USERS")
        if not sheet:
            self._demo_users[wa_id] = {
                "wa_id": wa_id,
                "name": merged_name,
                "address": merged_address,
                "last_order_date": last_order_date,
                "last_order_items": merged_items,
                "last_seen": now,
            }
            return

        payload_items = json.dumps(merged_items, ensure_ascii=False) if merged_items else ""
        user_payload = {
            "wa_id": wa_id,
            "name": merged_name,
            "address": merged_address,
            "last_order_date": last_order_date,
            "last_order_items": merged_items,
            "last_seen": now,
        }
        row_idx = self._resolve_user_row(sheet, wa_id)
        if row_idx:
            sheet.update(
                f"B{row_idx}:F{row_idx}",
                [
                    [
                        merged_name,
                        merged_address,
                        last_order_date,
                        payload_items,
                        now,
                    ]
                ],
            )
            with self._cache_lock:
                if self._users_cache is not None:
                    self._users_cache[wa_id] = user_payload
            return

        sheet.append_row(
            [wa_id, merged_name, merged_address, last_order_date, payload_items, now]
        )
        new_row = len(sheet.get_all_values())
        with self._cache_lock:
            if self._users_cache is not None:
                self._users_cache[wa_id] = user_payload
            if self._user_row_index is not None:
                self._user_row_index[wa_id] = new_row

    def create_order(
        self,
        wa_id: str,
        items: List[Dict[str, Any]],
        total: float,
        status: str = "pending",
        customer_name: str = "",
        address: str = "",
        delivery_type: str = "",
    ) -> str:
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        payload = {
            "order_id": order_id,
            "wa_id": wa_id,
            "items": items,
            "total": total,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "customer_name": customer_name,
            "address": address,
            "delivery_type": delivery_type,
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
                    customer_name,
                    address,
                    delivery_type,
                ]
            )
        else:
            self._demo_orders.append(payload)

        self._invalidate_orders_cache()
        self.upsert_user(
            wa_id=wa_id,
            name=customer_name,
            address=address,
            last_order_items=items,
        )
        return order_id

    def get_last_order(self, wa_id: str) -> Optional[Dict[str, Any]]:
        user = self.get_user(wa_id)
        items = user.get("last_order_items") or []
        if not items:
            return None
        return {
            "wa_id": wa_id,
            "items": items,
            "customer_name": user.get("name", ""),
            "address": user.get("address", ""),
            "last_order_date": user.get("last_order_date", ""),
        }

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        order_id = order_id.upper()
        for order in self._demo_orders:
            if order.get("order_id") == order_id:
                return dict(order)

        sheet = self._get_sheet("ORDERS")
        if not sheet:
            return None
        for row in self._get_orders_records():
            if str(row.get("order_id", "")).upper() == order_id:
                try:
                    items = json.loads(row.get("items") or "[]")
                except json.JSONDecodeError:
                    items = []
                return {
                    "order_id": row.get("order_id"),
                    "wa_id": str(row.get("wa_id", "")),
                    "items": items,
                    "total": float(row.get("total", 0) or 0),
                    "status": str(row.get("status", "pending")),
                    "timestamp": str(row.get("timestamp", "")),
                    "customer_name": str(row.get("customer_name", "")),
                    "address": str(row.get("address", "")),
                    "delivery_type": str(row.get("delivery_type", "")),
                }
        return None

    def update_order_status(self, order_id: str, status: str) -> bool:
        order_id = order_id.upper()
        for order in self._demo_orders:
            if order.get("order_id") == order_id:
                order["status"] = status
                return True

        sheet = self._get_sheet("ORDERS")
        if not sheet:
            return False
        rows = self._get_orders_records()
        for idx, row in enumerate(rows, start=2):
            if str(row.get("order_id", "")).upper() == order_id:
                sheet.update(f"E{idx}", [[status]])
                self._invalidate_orders_cache()
                return True
        return False

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        pending: List[Dict[str, Any]] = []
        for order in self._demo_orders:
            if order.get("status") == "pending":
                pending.append(dict(order))

        sheet = self._get_sheet("ORDERS")
        if not sheet:
            return pending

        for row in self._get_orders_records():
            if str(row.get("status", "")).lower() != "pending":
                continue
            try:
                items = json.loads(row.get("items") or "[]")
            except json.JSONDecodeError:
                items = []
            pending.append(
                {
                    "order_id": row.get("order_id"),
                    "wa_id": str(row.get("wa_id", "")),
                    "items": items,
                    "total": float(row.get("total", 0) or 0),
                    "status": "pending",
                    "timestamp": str(row.get("timestamp", "")),
                    "customer_name": str(row.get("customer_name", "")),
                    "address": str(row.get("address", "")),
                    "delivery_type": str(row.get("delivery_type", "")),
                }
            )
        return pending

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
