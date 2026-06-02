from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views import View

from .services import readers


class OrderListView(View):
    def get(self, request):
        status_filter = request.GET.get("status", "").strip().lower()
        orders = readers.read_orders()
        if status_filter:
            orders = [
                o
                for o in orders
                if str(o.get("status", "")).lower() == status_filter
            ]
        return render(
            request,
            "operations/order_list.html",
            {
                "orders": orders,
                "status_filter": status_filter,
            },
        )


class OrderDetailView(View):
    def get(self, request, order_id: str):
        order = readers.read_order(order_id)
        if not order:
            raise Http404("Pedido no encontrado")
        items = order.get("items") or []
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except json.JSONDecodeError:
                items = []
        return render(
            request,
            "operations/order_detail.html",
            {"order": order, "items": items},
        )


class ReservationListView(View):
    def get(self, request):
        return render(
            request,
            "operations/reservation_list.html",
            {"reservations": readers.read_reservations()},
        )


class MenuView(View):
    def get(self, request):
        return render(
            request,
            "operations/menu.html",
            {"menu_by_category": readers.menu_by_category()},
        )


class UserListView(View):
    def get(self, request):
        return render(
            request,
            "operations/user_list.html",
            {"users": readers.read_users()},
        )


class SystemStatusView(View):
    def get(self, request):
        bot_health, bot_health_error = _fetch_bot_health()
        bot_health_text = (
            json.dumps(bot_health, indent=2, ensure_ascii=False)
            if bot_health
            else ""
        )
        sheets_cache = readers.sheets_cache_status()
        sheets_cache_text = json.dumps(
            sheets_cache, indent=2, ensure_ascii=False
        )
        return render(
            request,
            "operations/system_status.html",
            {
                "bot_health_text": bot_health_text,
                "bot_health_error": bot_health_error,
                "sheets_cache_text": sheets_cache_text,
                "bot_health_url": settings.BOT_HEALTH_URL,
            },
        )


def _fetch_bot_health():
    url = settings.BOT_HEALTH_URL
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            body = response.read().decode("utf-8")
            return json.loads(body), ""
    except urllib.error.URLError as exc:
        return None, str(exc)
    except (json.JSONDecodeError, TimeoutError, OSError) as exc:
        return None, str(exc)
