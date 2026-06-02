from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.audit import log_audit
from services import bot_bridge

from .services import readers


class OrderListView(LoginRequiredMixin, View):
    def get(self, request):
        status_filter = request.GET.get("status", "").strip().lower()
        log_audit(
            request,
            action="view",
            entity="orders",
            metadata={"status_filter": status_filter or None},
        )
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


class OrderDetailView(LoginRequiredMixin, View):
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
            {
                "order": order,
                "items": items,
                "can_confirm": (
                    bot_bridge.writes_enabled()
                    and str(order.get("status", "")).lower() == "pending"
                ),
            },
        )

    def post(self, request, order_id: str):
        if request.POST.get("action") != "confirm":
            raise Http404()
        order = readers.read_order(order_id)
        if not order:
            raise Http404("Pedido no encontrado")

        result = bot_bridge.confirm_order(order_id)
        log_audit(
            request,
            action="confirm_order",
            entity="order",
            entity_id=order_id.upper(),
            metadata={
                "ok": result.ok,
                "already_confirmed": result.already_confirmed,
                "message": result.message,
            },
        )
        if result.ok:
            messages.success(request, result.message)
        elif result.already_confirmed:
            messages.warning(request, result.message)
        else:
            messages.error(request, result.message)
        return redirect("operations:order_detail", order_id=order_id.upper())


class ReservationListView(LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "operations/reservation_list.html",
            {"reservations": readers.read_reservations()},
        )


class MenuView(LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "operations/menu.html",
            {"menu_by_category": readers.menu_by_category()},
        )

    def post(self, request):
        if request.POST.get("action") != "unavailable":
            raise Http404()
        item_id = request.POST.get("item_id", "").strip()
        ok, message = bot_bridge.set_menu_item_unavailable(item_id)
        log_audit(
            request,
            action="menu_unavailable",
            entity="menu_item",
            entity_id=item_id,
            metadata={"ok": ok, "message": message},
        )
        if ok:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect("operations:menu")


class UserListView(LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "operations/user_list.html",
            {"users": readers.read_users()},
        )


class SystemStatusView(LoginRequiredMixin, View):
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
