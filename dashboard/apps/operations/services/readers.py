"""Read-only access to bot cache JSON with optional GoogleSheetsClient fallback."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings

DATA_DIR = settings.PROJECT_ROOT / "data"
MENU_PATH = DATA_DIR / "menu_cache.json"
ORDERS_PATH = DATA_DIR / "orders_cache.json"
USERS_PATH = DATA_DIR / "users_cache.json"
RESERVATIONS_PATH = DATA_DIR / "reservations_cache.json"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None


def _ensure_app_importable() -> None:
    root = str(settings.PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _sheets_client():
    _ensure_app_importable()
    from app.config import GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_ID
    from app.integrations.google_sheets import get_google_sheets_client

    return get_google_sheets_client(
        GOOGLE_SHEETS_CREDENTIALS_PATH,
        GOOGLE_SPREADSHEET_ID,
    )


def read_menu() -> List[Dict[str, Any]]:
    raw = _load_json(MENU_PATH)
    if isinstance(raw, list) and raw:
        return raw
    return _sheets_client().get_menu()


def read_orders() -> List[Dict[str, Any]]:
    raw = _load_json(ORDERS_PATH)
    orders: List[Dict[str, Any]] = []
    if isinstance(raw, dict):
        bucket = raw.get("orders", {})
        if isinstance(bucket, dict) and bucket:
            orders = [dict(v) for v in bucket.values()]
    if orders:
        return _sort_orders(orders)
    client = _sheets_client()
    client.warm_up_cache()
    raw = _load_json(ORDERS_PATH)
    if isinstance(raw, dict):
        bucket = raw.get("orders", {})
        if isinstance(bucket, dict) and bucket:
            return _sort_orders([dict(v) for v in bucket.values()])
    return _sort_orders(client.get_pending_orders())


def read_order(order_id: str) -> Optional[Dict[str, Any]]:
    order_id = order_id.upper()
    raw = _load_json(ORDERS_PATH)
    if isinstance(raw, dict):
        bucket = raw.get("orders", {})
        if isinstance(bucket, dict):
            for key, value in bucket.items():
                if str(key).upper() == order_id:
                    return dict(value)
    return _sheets_client().get_order(order_id)


def read_users() -> List[Dict[str, Any]]:
    raw = _load_json(USERS_PATH)
    users: List[Dict[str, Any]] = []
    if isinstance(raw, dict):
        bucket = raw.get("users", {})
        if isinstance(bucket, dict) and bucket:
            users = [dict(v) for v in bucket.values()]
    if users:
        return _sort_users(users)
    client = _sheets_client()
    client.warm_up_cache()
    raw = _load_json(USERS_PATH)
    if isinstance(raw, dict):
        bucket = raw.get("users", {})
        if isinstance(bucket, dict) and bucket:
            return _sort_users([dict(v) for v in bucket.values()])
    return []


def read_reservations() -> List[Dict[str, Any]]:
    raw = _load_json(RESERVATIONS_PATH)
    reservations: List[Dict[str, Any]] = []
    if isinstance(raw, dict):
        bucket = raw.get("reservations", {})
        if isinstance(bucket, dict) and bucket:
            reservations = [dict(v) for v in bucket.values()]
    if reservations:
        return _sort_reservations(reservations)
    client = _sheets_client()
    client.warm_up_cache()
    raw = _load_json(RESERVATIONS_PATH)
    if isinstance(raw, dict):
        bucket = raw.get("reservations", {})
        if isinstance(bucket, dict) and bucket:
            return _sort_reservations([dict(v) for v in bucket.values()])
    return []


def sheets_cache_status() -> Dict[str, Any]:
    try:
        return _sheets_client().cache_status()
    except Exception as exc:
        return {"ready": False, "error": str(exc)}


def menu_by_category() -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in read_menu():
        category = str(item.get("categoria") or "Sin categoría")
        grouped.setdefault(category, []).append(item)
    for items in grouped.values():
        items.sort(key=lambda i: str(i.get("nombre", "")).lower())
    return dict(sorted(grouped.items(), key=lambda kv: kv[0].lower()))


def _sort_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        orders,
        key=lambda o: str(o.get("timestamp", "")),
        reverse=True,
    )


def _sort_users(users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        users,
        key=lambda u: str(u.get("last_seen", "")),
        reverse=True,
    )


def _sort_reservations(reservations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        reservations,
        key=lambda r: (str(r.get("fecha", "")), str(r.get("hora", ""))),
        reverse=True,
    )
