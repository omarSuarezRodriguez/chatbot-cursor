"""Read-only access to bot cache JSON with optional GoogleSheetsClient fallback."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

DATA_DIR = settings.PROJECT_ROOT / "data"
MENU_PATH = DATA_DIR / "menu_cache.json"
ORDERS_PATH = DATA_DIR / "orders_cache.json"
USERS_PATH = DATA_DIR / "users_cache.json"
RESERVATIONS_PATH = DATA_DIR / "reservations_cache.json"

ORDER_STATUSES = ("pending", "confirmed", "delivered", "cancelled")
ORDER_SORT_FIELDS = ("timestamp", "total", "customer_name", "order_id", "status")


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


def _order_total(order: Dict[str, Any]) -> float:
    try:
        return float(order.get("total") or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_order_date(order: Dict[str, Any]) -> Optional[date]:
    raw = order.get("timestamp")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw)).date()
    except ValueError:
        return None


def dashboard_kpis() -> Dict[str, Any]:
    orders = read_orders()
    return {
        "orders_count": len(orders),
        "sales_total": round(sum(_order_total(o) for o in orders), 2),
        "customers_count": len(read_users()),
        "reservations_count": len(read_reservations()),
        "conversations_count": len(read_users()),
    }


def chart_orders_by_status() -> Dict[str, Any]:
    labels_es = {
        "pending": "Pendientes",
        "confirmed": "Confirmados",
        "delivered": "Entregados",
        "cancelled": "Cancelados",
    }
    counts = {s: 0 for s in ORDER_STATUSES}
    other = 0
    for order in read_orders():
        status = str(order.get("status", "")).lower() or "pending"
        if status in counts:
            counts[status] += 1
        else:
            other += 1
    labels: List[str] = [labels_es[s] for s in ORDER_STATUSES if counts[s]]
    values: List[int] = [counts[s] for s in ORDER_STATUSES if counts[s]]
    if other:
        labels.append("Otros")
        values.append(other)
    return {"labels": labels, "values": values}


def chart_sales_by_day(days: int = 14) -> Dict[str, Any]:
    days = max(1, min(days, 90))
    end = date.today()
    start = end - timedelta(days=days - 1)
    buckets: Dict[str, float] = {}
    cursor = start
    while cursor <= end:
        buckets[cursor.isoformat()] = 0.0
        cursor += timedelta(days=1)
    for order in read_orders():
        order_date = _parse_order_date(order)
        if not order_date or order_date < start or order_date > end:
            continue
        key = order_date.isoformat()
        buckets[key] = buckets.get(key, 0.0) + _order_total(order)
    labels = [
        datetime.fromisoformat(k).strftime("%d/%m")
        for k in sorted(buckets.keys())
    ]
    values = [round(buckets[k], 2) for k in sorted(buckets.keys())]
    return {"labels": labels, "values": values}


def query_orders(
    *,
    q: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
    sort: str = "timestamp",
    direction: str = "desc",
) -> List[Dict[str, Any]]:
    orders = read_orders()
    needle = q.strip().lower()
    status_filter = status.strip().lower()
    from_date = _parse_date_param(date_from)
    to_date = _parse_date_param(date_to)

    if needle:
        orders = [
            o
            for o in orders
            if needle in str(o.get("order_id", "")).lower()
            or needle in str(o.get("customer_name", "")).lower()
            or needle in str(o.get("wa_id", "")).lower()
        ]
    if status_filter:
        orders = [
            o
            for o in orders
            if str(o.get("status", "")).lower() == status_filter
        ]
    if from_date or to_date:
        filtered: List[Dict[str, Any]] = []
        for order in orders:
            order_date = _parse_order_date(order)
            if not order_date:
                continue
            if from_date and order_date < from_date:
                continue
            if to_date and order_date > to_date:
                continue
            filtered.append(order)
        orders = filtered

    sort_field = sort if sort in ORDER_SORT_FIELDS else "timestamp"
    reverse = direction.lower() != "asc"
    return sorted(orders, key=lambda o: _order_sort_key(o, sort_field), reverse=reverse)


def _parse_date_param(value: str) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _order_sort_key(order: Dict[str, Any], field: str) -> Tuple[Any, ...]:
    if field == "total":
        return (_order_total(order),)
    if field == "customer_name":
        return (str(order.get("customer_name", "")).lower(),)
    if field == "order_id":
        return (str(order.get("order_id", "")).upper(),)
    if field == "status":
        return (str(order.get("status", "")).lower(),)
    return (str(order.get("timestamp", "")),)
