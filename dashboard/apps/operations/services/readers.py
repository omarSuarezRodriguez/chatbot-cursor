"""Read-only access to bot cache JSON with optional GoogleSheetsClient fallback."""

from __future__ import annotations

import json
import os
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
_STATUS_PRIORITY = {
    "pending": 0,
    "confirmed": 1,
    "delivered": 2,
    "cancelled": 3,
}


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None


def _prefer_remote() -> bool:
    return bool(
        os.environ.get("GOOGLE_SPREADSHEET_ID", "").strip()
        and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    )


def _orders_from_cache_payload(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    bucket = raw.get("orders", {})
    if not isinstance(bucket, dict) or not bucket:
        return []
    return [dict(v) for v in bucket.values()]


def _orders_from_local_cache() -> List[Dict[str, Any]]:
    return _orders_from_cache_payload(_load_json(ORDERS_PATH))


def _parse_orders_sheet_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    orders: List[Dict[str, Any]] = []
    for row in rows:
        order_id = str(row.get("order_id", "")).strip().upper()
        if not order_id:
            continue
        try:
            items = json.loads(row.get("items") or "[]")
        except (json.JSONDecodeError, TypeError):
            items = []
        try:
            total = float(row.get("total", 0) or 0)
        except (TypeError, ValueError):
            total = 0.0
        orders.append(
            {
                "order_id": order_id,
                "wa_id": str(row.get("wa_id", "")),
                "items": items,
                "total": total,
                "status": str(row.get("status", "pending")).lower(),
                "timestamp": str(row.get("timestamp", "")),
                "customer_name": str(row.get("customer_name", "")),
                "address": str(row.get("address", "")),
                "delivery_type": str(row.get("delivery_type", "")),
            }
        )
    return orders


def _remote_orders_from_sheets() -> List[Dict[str, Any]]:
    client = _sheets_client()
    if hasattr(client, "_records"):
        return _parse_orders_sheet_rows(client._records("ORDERS"))
    if hasattr(client, "warm_up_cache"):
        client.warm_up_cache()
    return _orders_from_local_cache()


def _merge_order_lists(*lists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    combined: List[Dict[str, Any]] = []
    for orders in lists:
        combined.extend(orders)
    if not combined:
        return []
    return _sort_orders(combined)


def _ensure_app_importable() -> None:
    root = str(settings.PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _sheets_client():
    _ensure_app_importable()
    try:
        from app.config import GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_ID
        from app.integrations.google_sheets import get_google_sheets_client

        return get_google_sheets_client(
            GOOGLE_SHEETS_CREDENTIALS_PATH,
            GOOGLE_SPREADSHEET_ID,
        )
    except Exception:
        # Dashboard can run as standalone service (without /app bot package).
        class _FallbackSheetsClient:
            def _records(self, tab_name: str) -> List[Dict[str, Any]]:
                spreadsheet_id = os.environ.get("GOOGLE_SPREADSHEET_ID", "").strip()
                json_blob = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
                if not spreadsheet_id or not json_blob:
                    return []
                try:
                    import gspread
                    from google.oauth2.service_account import Credentials

                    scopes = [
                        "https://www.googleapis.com/auth/spreadsheets.readonly",
                        "https://www.googleapis.com/auth/drive.readonly",
                    ]
                    creds = Credentials.from_service_account_info(
                        json.loads(json_blob),
                        scopes=scopes,
                    )
                    client = gspread.authorize(creds)
                    ws = client.open_by_key(spreadsheet_id).worksheet(tab_name)
                    return ws.get_all_records()
                except Exception:
                    return []

            def warm_up_cache(self) -> None:
                return

            def get_menu(self) -> List[Dict[str, Any]]:
                rows = self._records("MENU")
                menu: List[Dict[str, Any]] = []
                for row in rows:
                    if not row.get("nombre"):
                        continue
                    try:
                        price = float(row.get("precio", 0) or 0)
                    except (TypeError, ValueError):
                        price = 0.0
                    disponible_raw = str(row.get("disponible", "true")).strip().lower()
                    disponible = disponible_raw in {
                        "1",
                        "true",
                        "si",
                        "sí",
                        "yes",
                        "y",
                    }
                    menu.append(
                        {
                            "id": str(row.get("id", "")).strip(),
                            "nombre": str(row.get("nombre", "")).strip(),
                            "precio": price,
                            "categoria": str(row.get("categoria", "")).strip(),
                            "disponible": disponible,
                        }
                    )
                return menu

            def get_pending_orders(self) -> List[Dict[str, Any]]:
                rows = self._records("ORDERS")
                orders: List[Dict[str, Any]] = []
                for row in rows:
                    order_id = str(row.get("order_id", "")).strip().upper()
                    if not order_id:
                        continue
                    try:
                        items = json.loads(row.get("items") or "[]")
                    except Exception:
                        items = []
                    try:
                        total = float(row.get("total", 0) or 0)
                    except (TypeError, ValueError):
                        total = 0.0
                    orders.append(
                        {
                            "order_id": order_id,
                            "wa_id": str(row.get("wa_id", "")),
                            "items": items,
                            "total": total,
                            "status": str(row.get("status", "pending")).lower(),
                            "timestamp": str(row.get("timestamp", "")),
                            "customer_name": str(row.get("customer_name", "")),
                            "address": str(row.get("address", "")),
                            "delivery_type": str(row.get("delivery_type", "")),
                        }
                    )
                return orders

            def get_order(self, _order_id: str) -> Optional[Dict[str, Any]]:
                needle = str(_order_id).strip().upper()
                for order in self.get_pending_orders():
                    if str(order.get("order_id", "")).upper() == needle:
                        return order
                return None

            def get_user(self, _wa_id: str) -> Dict[str, Any]:
                wa_id = str(_wa_id).strip()
                rows = self._records("USERS")
                for row in rows:
                    if str(row.get("wa_id", "")).strip() == wa_id:
                        return {
                            "wa_id": wa_id,
                            "name": str(row.get("name", "")).strip(),
                            "address": str(row.get("address", "")).strip(),
                            "last_order_date": str(row.get("last_order_date", "")).strip(),
                            "last_order_items": [],
                            "last_seen": str(row.get("last_seen", "")).strip(),
                        }
                return {}

            def cache_status(self) -> Dict[str, Any]:
                return {
                    "ready": True,
                    "sheets_connected": True,
                    "menu_items": len(self.get_menu()),
                    "orders": len(self.get_pending_orders()),
                }

        return _FallbackSheetsClient()


def read_menu() -> List[Dict[str, Any]]:
    if _prefer_remote():
        menu = _sheets_client().get_menu()
        if menu:
            return menu
    raw = _load_json(MENU_PATH)
    if isinstance(raw, list) and raw:
        return raw
    return _sheets_client().get_menu()


def read_orders() -> List[Dict[str, Any]]:
    """All orders (any status). Prefer local bot cache; merge with Sheets when configured."""
    local = _orders_from_local_cache()
    if _prefer_remote():
        remote = _remote_orders_from_sheets()
        if local or remote:
            return _merge_order_lists(local, remote)
    if local:
        return _sort_orders(local)
    remote = _remote_orders_from_sheets()
    if remote:
        return _sort_orders(remote)
    return []


def read_order(order_id: str) -> Optional[Dict[str, Any]]:
    order_id = order_id.upper()
    for order in read_orders():
        if str(order.get("order_id", "")).upper() == order_id:
            return order
    return _sheets_client().get_order(order_id)


def read_user(wa_id: str) -> Optional[Dict[str, Any]]:
    wa_id = str(wa_id).strip()
    for user in read_users():
        if str(user.get("wa_id", "")).strip() == wa_id:
            return dict(user)
    profile = _sheets_client().get_user(wa_id)
    return profile if profile.get("wa_id") else None


def read_menu_item(item_id: str) -> Optional[Dict[str, Any]]:
    item_id = str(item_id).strip()
    for item in read_menu():
        if str(item.get("id", "")).strip() == item_id:
            return dict(item)
    return None


def menu_categories() -> List[str]:
    categories = sorted(
        {str(i.get("categoria") or "General") for i in read_menu()},
        key=str.lower,
    )
    return categories


def read_users() -> List[Dict[str, Any]]:
    if _prefer_remote():
        client = _sheets_client()
        rows = client._records("USERS") if hasattr(client, "_records") else []
        if rows:
            parsed = []
            for row in rows:
                wa_id = str(row.get("wa_id", "")).strip()
                if not wa_id:
                    continue
                parsed.append(
                    {
                        "wa_id": wa_id,
                        "name": str(row.get("name", "")).strip(),
                        "address": str(row.get("address", "")).strip(),
                        "last_order_date": str(row.get("last_order_date", "")).strip(),
                        "last_order_items": [],
                        "last_seen": str(row.get("last_seen", "")).strip(),
                    }
                )
            if parsed:
                return _sort_users(parsed)
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
    if _prefer_remote():
        client = _sheets_client()
        rows = client._records("RESERVATIONS") if hasattr(client, "_records") else []
        if rows:
            parsed = []
            for row in rows:
                rid = str(row.get("reservation_id", "")).strip()
                if not rid:
                    continue
                parsed.append(
                    {
                        "reservation_id": rid,
                        "wa_id": str(row.get("wa_id", "")).strip(),
                        "personas": int(row.get("personas", 0) or 0),
                        "fecha": str(row.get("fecha", "")).strip(),
                        "hora": str(row.get("hora", "")).strip(),
                        "status": str(row.get("status", "confirmed")).strip(),
                    }
                )
            if parsed:
                return _sort_reservations(parsed)
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
    deduped: Dict[str, Dict[str, Any]] = {}
    for order in orders:
        oid = str(order.get("order_id", "")).strip().upper()
        if not oid:
            continue
        candidate = dict(order)
        candidate["order_id"] = oid
        prev = deduped.get(oid)
        if prev is None:
            deduped[oid] = candidate
            continue
        prev_ts = str(prev.get("timestamp", ""))
        cand_ts = str(candidate.get("timestamp", ""))
        prev_status = str(prev.get("status", "")).lower()
        cand_status = str(candidate.get("status", "")).lower()
        prev_rank = _STATUS_PRIORITY.get(prev_status, -1)
        cand_rank = _STATUS_PRIORITY.get(cand_status, -1)
        # Prefer more advanced lifecycle status; tie-break by newer timestamp.
        if cand_rank > prev_rank or (cand_rank == prev_rank and cand_ts > prev_ts):
            deduped[oid] = candidate

    return sorted(
        deduped.values(),
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


def read_reservation(reservation_id: str) -> Optional[Dict[str, Any]]:
    rid = str(reservation_id).strip().upper()
    if not rid:
        return None
    for reservation in read_reservations():
        if str(reservation.get("reservation_id", "")).strip().upper() == rid:
            return reservation
    return None


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
