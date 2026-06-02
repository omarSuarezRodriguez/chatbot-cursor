from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.accounts.audit import log_audit
from services import bot_bridge

from .forms import (
    CustomerForm,
    MenuItemForm,
    OrderCreateForm,
    OrderItemsForm,
    OrderStatusForm,
    PanelSettingsForm,
    PanelStaffForm,
)
from .permissions import (
    GROUP_ADMIN,
    GROUP_OPERATOR,
    AdminRequiredMixin,
    OperatorRequiredMixin,
    user_is_dashboard_admin,
    user_is_dashboard_operator,
)
from .services import readers
from .services.settings_store import load_panel_settings, save_panel_settings

ORDERS_PER_PAGE = 20
ORDER_LIST_TAB_STATUSES = (
    ("pending", "Pendiente"),
    ("confirmed", "Confirmado"),
    ("delivered", "Entregado"),
)


def _flash_write_result(request, result, *, success_level="success"):
    if result.ok:
        messages.success(request, result.message)
    elif getattr(result, "already_confirmed", False):
        messages.warning(request, result.message)
    else:
        messages.error(request, result.message)


class DashboardHomeView(LoginRequiredMixin, View):
    def get(self, request):
        log_audit(request, action="view", entity="dashboard_home")
        return render(
            request,
            "operations/dashboard_home.html",
            {
                "kpis": readers.dashboard_kpis(),
                "chart_by_status": readers.chart_orders_by_status(),
                "chart_sales": readers.chart_sales_by_day(),
            },
        )


class OrderListView(LoginRequiredMixin, View):
    def get(self, request):
        panel = load_panel_settings()
        q = request.GET.get("q", "").strip()
        status_from_request = request.GET.get("status")
        if status_from_request is None:
            status_filter = (
                panel.get("default_order_status_filter", "") or "pending"
            ).strip().lower()
        else:
            status_filter = status_from_request.strip().lower()
        date_from = request.GET.get("date_from", "").strip()
        date_to = request.GET.get("date_to", "").strip()
        sort = request.GET.get("sort", "timestamp").strip()
        direction = request.GET.get("dir", "desc").strip()
        per_page = panel.get("orders_per_page", ORDERS_PER_PAGE)
        try:
            page_num = max(1, int(request.GET.get("page", "1")))
        except ValueError:
            page_num = 1

        log_audit(
            request,
            action="view",
            entity="orders",
            metadata={
                "status_filter": status_filter or None,
                "q": q or None,
                "date_from": date_from or None,
                "date_to": date_to or None,
                "sort": sort,
                "dir": direction,
                "page": page_num,
            },
        )
        orders = readers.query_orders(
            q=q,
            status=status_filter,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
            direction=direction,
        )
        if not panel.get("show_cancelled_orders", True) and not status_filter:
            orders = [
                o for o in orders if str(o.get("status", "")).lower() != "cancelled"
            ]
        paginator = Paginator(orders, per_page)
        page_obj = paginator.get_page(page_num)

        query_params = request.GET.copy()
        query_params.pop("page", None)
        base_query = query_params.urlencode()
        tab_query_params = query_params.copy()
        tab_query_params.pop("status", None)
        base_query_for_tabs = tab_query_params.urlencode()

        can_confirm_orders = bot_bridge.writes_enabled() and user_is_dashboard_operator(
            request.user
        )

        return render(
            request,
            "operations/order_list.html",
            {
                "page_obj": page_obj,
                "orders": page_obj.object_list,
                "q": q,
                "status_filter": status_filter,
                "date_from": date_from,
                "date_to": date_to,
                "sort": sort,
                "direction": direction,
                "order_statuses": readers.ORDER_STATUSES,
                "order_status_tabs": ORDER_LIST_TAB_STATUSES,
                "sort_fields": readers.ORDER_SORT_FIELDS,
                "base_query": base_query,
                "base_query_for_tabs": base_query_for_tabs,
                "can_confirm_orders": can_confirm_orders,
                "can_create_order": can_confirm_orders,
            },
        )


class OrderCreateView(OperatorRequiredMixin, LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "operations/order_form.html",
            {"form": OrderCreateForm()},
        )

    def post(self, request):
        form = OrderCreateForm(request.POST)
        if not form.is_valid():
            return render(request, "operations/order_form.html", {"form": form})

        result = bot_bridge.create_manual_order(
            wa_id=form.cleaned_data["wa_id"],
            items=form.cleaned_items,
            customer_name=form.cleaned_data.get("customer_name", ""),
            address=form.cleaned_data.get("address", ""),
            delivery_type=form.cleaned_data.get("delivery_type", ""),
        )
        log_audit(
            request,
            action="create_order",
            entity="order",
            entity_id=result.entity_id,
            metadata={"ok": result.ok, "message": result.message},
        )
        if result.ok:
            messages.success(request, result.message)
            return redirect("operations:order_detail", order_id=result.entity_id)
        messages.error(request, result.message)
        return render(request, "operations/order_form.html", {"form": form})


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
        can_write = bot_bridge.writes_enabled() and user_is_dashboard_operator(
            request.user
        )
        status = str(order.get("status", "")).lower()
        return render(
            request,
            "operations/order_detail.html",
            {
                "order": order,
                "items": items,
                "can_confirm": can_write and status == "pending",
                "can_edit": can_write and status != "cancelled",
                "status_form": OrderStatusForm(initial={"status": status or "pending"}),
                "items_form": OrderItemsForm(initial_items=items),
            },
        )

    def post(self, request, order_id: str):
        if not bot_bridge.writes_enabled():
            messages.error(request, bot_bridge._disabled().message)
            return redirect("operations:order_detail", order_id=order_id.upper())
        if not user_is_dashboard_operator(request.user):
            raise Http404()

        action = request.POST.get("action", "")
        order = readers.read_order(order_id)
        if not order:
            raise Http404("Pedido no encontrado")
        order_id = order_id.upper()

        if action == "confirm":
            result = bot_bridge.confirm_order(order_id)
            audit_action = "confirm_order"
        elif action == "cancel":
            result = bot_bridge.cancel_order(order_id)
            audit_action = "cancel_order"
        elif action == "update_status":
            form = OrderStatusForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Estado inválido.")
                return redirect("operations:order_detail", order_id=order_id)
            result = bot_bridge.update_order_status(
                order_id, form.cleaned_data["status"]
            )
            audit_action = "update_order_status"
        elif action == "update_items":
            form = OrderItemsForm(request.POST)
            if not form.is_valid():
                messages.error(request, "; ".join(form.errors.get("items_json", [])))
                return redirect("operations:order_detail", order_id=order_id)
            result = bot_bridge.update_order_items(order_id, form.cleaned_items)
            audit_action = "update_order_items"
        else:
            raise Http404()

        log_audit(
            request,
            action=audit_action,
            entity="order",
            entity_id=order_id,
            metadata={"ok": result.ok, "message": result.message},
        )
        if action == "confirm" and getattr(result, "already_confirmed", False):
            messages.success(request, f"Pedido {order_id} ya estaba confirmado.")
        else:
            _flash_write_result(request, result)
        if request.POST.get("return_to_list") == "1":
            return redirect(f"{reverse('operations:orders')}?status=pending")
        return redirect("operations:order_detail", order_id=order_id)


class ReservationListView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip().lower()
        reservations = readers.read_reservations()
        if q:
            reservations = [
                r
                for r in reservations
                if q in str(r.get("reservation_id", "")).lower()
                or q in str(r.get("wa_id", "")).lower()
                or q in str(r.get("status", "")).lower()
            ]
        log_audit(
            request,
            action="view",
            entity="reservations",
            metadata={"q": q or None, "count": len(reservations)},
        )
        return render(
            request,
            "operations/reservation_list.html",
            {"reservations": reservations, "q": q},
        )


class ReservationDetailView(LoginRequiredMixin, View):
    def get(self, request, reservation_id: str):
        reservation = readers.read_reservation(reservation_id)
        if not reservation:
            raise Http404("Reserva no encontrada")
        log_audit(
            request,
            action="view",
            entity="reservation",
            entity_id=str(reservation.get("reservation_id", "")),
        )
        return render(
            request,
            "operations/reservation_detail.html",
            {"reservation": reservation},
        )


class MenuView(LoginRequiredMixin, View):
    def get(self, request):
        can_admin = user_is_dashboard_admin(request.user)
        can_operate = bot_bridge.writes_enabled() and (
            can_admin or user_is_dashboard_operator(request.user)
        )
        return render(
            request,
            "operations/menu.html",
            {
                "menu_by_category": readers.menu_by_category(),
                "can_create": can_admin and bot_bridge.writes_enabled(),
                "can_operate": can_operate,
            },
        )

    def post(self, request):
        action = request.POST.get("action", "")
        if action == "unavailable":
            if not user_is_dashboard_operator(request.user):
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
        if action == "available":
            if not user_is_dashboard_operator(request.user):
                raise Http404()
            item_id = request.POST.get("item_id", "").strip()
            ok, message = bot_bridge.set_menu_item_availability(item_id, True)
            log_audit(
                request,
                action="menu_available",
                entity="menu_item",
                entity_id=item_id,
                metadata={"ok": ok, "message": message},
            )
            if ok:
                messages.success(request, message)
            else:
                messages.error(request, message)
            return redirect("operations:menu")
        raise Http404()


class MenuItemCreateView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "operations/menu_form.html",
            {"form": MenuItemForm(is_new=True), "is_new": True},
        )

    def post(self, request):
        form = MenuItemForm(request.POST, is_new=True)
        if not form.is_valid():
            return render(
                request,
                "operations/menu_form.html",
                {"form": form, "is_new": True},
            )
        data = form.cleaned_data
        result = bot_bridge.save_menu_item(
            data["item_id"],
            data["nombre"],
            float(data["precio"]),
            data["categoria"],
            data.get("disponible", False),
            is_new=True,
        )
        log_audit(
            request,
            action="create_menu_item",
            entity="menu_item",
            entity_id=result.entity_id,
            metadata={"ok": result.ok, "message": result.message},
        )
        if result.ok:
            messages.success(request, result.message)
            return redirect("operations:menu")
        messages.error(request, result.message)
        return render(
            request,
            "operations/menu_form.html",
            {"form": form, "is_new": True},
        )


class MenuItemEditView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, item_id: str):
        item = readers.read_menu_item(item_id)
        if not item:
            raise Http404("Plato no encontrado")
        form = MenuItemForm(
            initial={
                "item_id": item.get("id", ""),
                "nombre": item.get("nombre", ""),
                "precio": item.get("precio", 0),
                "categoria": item.get("categoria", ""),
                "disponible": item.get("disponible", True),
            },
            is_new=False,
        )
        return render(
            request,
            "operations/menu_form.html",
            {"form": form, "is_new": False, "item": item},
        )

    def post(self, request, item_id: str):
        form = MenuItemForm(request.POST, is_new=False)
        if not form.is_valid():
            return render(
                request,
                "operations/menu_form.html",
                {"form": form, "is_new": False},
            )
        data = form.cleaned_data
        result = bot_bridge.save_menu_item(
            data["item_id"],
            data["nombre"],
            float(data["precio"]),
            data["categoria"],
            data.get("disponible", False),
            is_new=False,
        )
        log_audit(
            request,
            action="update_menu_item",
            entity="menu_item",
            entity_id=result.entity_id,
            metadata={"ok": result.ok, "message": result.message},
        )
        if result.ok:
            messages.success(request, result.message)
            return redirect("operations:menu")
        messages.error(request, result.message)
        return render(
            request,
            "operations/menu_form.html",
            {"form": form, "is_new": False},
        )


class MenuItemDeleteView(AdminRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, item_id: str):
        hard = request.POST.get("hard") == "1"
        result = bot_bridge.delete_menu_item(item_id, hard=hard)
        log_audit(
            request,
            action="delete_menu_item",
            entity="menu_item",
            entity_id=result.entity_id or item_id,
            metadata={"ok": result.ok, "hard": hard, "message": result.message},
        )
        _flash_write_result(request, result)
        return redirect("operations:menu")


class UserListView(LoginRequiredMixin, View):
    def get(self, request):
        can_write = bot_bridge.writes_enabled() and user_is_dashboard_operator(
            request.user
        )
        return render(
            request,
            "operations/user_list.html",
            {
                "users": readers.read_users(),
                "can_create": can_write,
                "is_admin": user_is_dashboard_admin(request.user),
            },
        )


class CustomerCreateView(OperatorRequiredMixin, LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "operations/customer_form.html",
            {"form": CustomerForm(is_new=True), "is_new": True},
        )

    def post(self, request):
        form = CustomerForm(request.POST, is_new=True)
        if not form.is_valid():
            return render(
                request,
                "operations/customer_form.html",
                {"form": form, "is_new": True},
            )
        data = form.cleaned_data
        result = bot_bridge.save_customer(
            data["wa_id"],
            name=data["name"],
            notes=data.get("notes", ""),
            is_new=True,
        )
        log_audit(
            request,
            action="create_customer",
            entity="customer",
            entity_id=result.entity_id,
            metadata={"ok": result.ok, "message": result.message},
        )
        if result.ok:
            messages.success(request, result.message)
            return redirect("operations:customer_detail", wa_id=result.entity_id)
        messages.error(request, result.message)
        return render(
            request,
            "operations/customer_form.html",
            {"form": form, "is_new": True},
        )


class CustomerDetailView(LoginRequiredMixin, View):
    def get(self, request, wa_id: str):
        user = readers.read_user(wa_id)
        if not user:
            raise Http404("Cliente no encontrado")
        can_write = bot_bridge.writes_enabled() and user_is_dashboard_operator(
            request.user
        )
        return render(
            request,
            "operations/customer_detail.html",
            {
                "customer": user,
                "can_edit": can_write,
                "can_delete": can_write and user_is_dashboard_admin(request.user),
            },
        )


class CustomerEditView(OperatorRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, wa_id: str):
        user = readers.read_user(wa_id)
        if not user:
            raise Http404("Cliente no encontrado")
        form = CustomerForm(
            initial={
                "wa_id": user.get("wa_id", ""),
                "name": user.get("name", ""),
                "notes": user.get("notes", ""),
            },
            is_new=False,
        )
        return render(
            request,
            "operations/customer_form.html",
            {"form": form, "is_new": False, "customer": user},
        )

    def post(self, request, wa_id: str):
        form = CustomerForm(request.POST, is_new=False)
        if not form.is_valid():
            return render(
                request,
                "operations/customer_form.html",
                {"form": form, "is_new": False},
            )
        data = form.cleaned_data
        result = bot_bridge.save_customer(
            data["wa_id"],
            name=data["name"],
            notes=data.get("notes", ""),
            is_new=False,
        )
        log_audit(
            request,
            action="update_customer",
            entity="customer",
            entity_id=result.entity_id,
            metadata={"ok": result.ok, "message": result.message},
        )
        if result.ok:
            messages.success(request, result.message)
            return redirect("operations:customer_detail", wa_id=result.entity_id)
        messages.error(request, result.message)
        return render(
            request,
            "operations/customer_form.html",
            {"form": form, "is_new": False},
        )


class CustomerDeleteView(AdminRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, wa_id: str):
        result = bot_bridge.delete_customer(wa_id)
        log_audit(
            request,
            action="delete_customer",
            entity="customer",
            entity_id=result.entity_id or wa_id,
            metadata={"ok": result.ok, "message": result.message},
        )
        _flash_write_result(request, result)
        return redirect("operations:users")


class PanelSettingsView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request):
        panel = load_panel_settings()
        form = PanelSettingsForm(initial=panel)
        return render(
            request,
            "operations/panel_settings.html",
            {"form": form, "storage": "PostgreSQL (accounts.DashboardSettings)"},
        )

    def post(self, request):
        form = PanelSettingsForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "operations/panel_settings.html",
                {"form": form, "storage": "PostgreSQL (accounts.DashboardSettings)"},
            )
        save_panel_settings(form.cleaned_data)
        log_audit(
            request,
            action="update_panel_settings",
            entity="panel_settings",
            metadata={"keys": list(form.cleaned_data.keys())},
        )
        messages.success(request, "Preferencias del panel guardadas.")
        return redirect("operations:panel_settings")


class AdminHubView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request):
        log_audit(request, action="view", entity="admin_hub")
        return render(request, "operations/admin_hub.html")


class WritesHelpView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "operations/writes_help.html")


class PanelStaffListView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request):
        staff = _panel_staff_users()
        return render(
            request,
            "operations/panel_staff_list.html",
            {"staff_users": staff, "can_manage": True},
        )


class PanelStaffCreateView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "operations/panel_staff_form.html",
            {"form": PanelStaffForm(is_new=True), "is_new": True},
        )

    def post(self, request):
        form = PanelStaffForm(request.POST, is_new=True)
        if not form.is_valid():
            return render(
                request,
                "operations/panel_staff_form.html",
                {"form": form, "is_new": True},
            )
        data = form.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            email=data.get("email", ""),
            password=data["password1"],
            is_staff=True,
        )
        user.is_active = data.get("is_active", True)
        user.save()
        _apply_panel_role(user, data["role"])
        log_audit(
            request,
            action="create_panel_user",
            entity="panel_user",
            entity_id=user.username,
            metadata={"role": data["role"]},
        )
        messages.success(request, f"Usuario {user.username} creado.")
        return redirect("operations:panel_staff_list")


class PanelStaffEditView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, user_id: int):
        user = _get_panel_user(user_id)
        form = PanelStaffForm(
            initial={
                "username": user.username,
                "email": user.email,
                "role": _panel_role_for_user(user),
                "is_active": user.is_active,
            },
            is_new=False,
        )
        return render(
            request,
            "operations/panel_staff_form.html",
            {"form": form, "is_new": False, "staff_user": user},
        )

    def post(self, request, user_id: int):
        user = _get_panel_user(user_id)
        form = PanelStaffForm(request.POST, is_new=False)
        if not form.is_valid():
            return render(
                request,
                "operations/panel_staff_form.html",
                {"form": form, "is_new": False, "staff_user": user},
            )
        data = form.cleaned_data
        if data["username"] != user.username:
            user.username = data["username"]
        user.email = data.get("email", "")
        user.is_active = data.get("is_active", False)
        if data.get("password1"):
            user.set_password(data["password1"])
        user.save()
        _apply_panel_role(user, data["role"])
        log_audit(
            request,
            action="update_panel_user",
            entity="panel_user",
            entity_id=user.username,
            metadata={"role": data["role"], "is_active": user.is_active},
        )
        messages.success(request, f"Usuario {user.username} actualizado.")
        return redirect("operations:panel_staff_list")


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
        bot_summary = _summarize_bot_health(bot_health)
        cache_summary = _summarize_sheets_cache(sheets_cache)
        log_audit(request, action="view", entity="system_status")
        return render(
            request,
            "operations/system_status.html",
            {
                "bot_health_text": bot_health_text,
                "bot_health_error": bot_health_error,
                "sheets_cache_text": sheets_cache_text,
                "bot_health_url": settings.BOT_HEALTH_URL,
                "bot_summary": bot_summary,
                "cache_summary": cache_summary,
                "writes_enabled": bot_bridge.writes_enabled(),
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


def _summarize_bot_health(data: dict | None) -> dict:
    if not data:
        return {
            "online": False,
            "status_label": "Sin conexión",
            "status_class": "status-pill--danger",
            "restaurant": "—",
            "admin_configured": False,
        }
    ok = str(data.get("status", "")).lower() == "ok"
    return {
        "online": ok,
        "status_label": "En línea" if ok else str(data.get("status", "desconocido")),
        "status_class": "status-pill--success" if ok else "status-pill--warning",
        "restaurant": data.get("restaurant") or data.get("service") or "—",
        "admin_configured": bool(data.get("admin_configured")),
        "service": data.get("service", ""),
    }


def _summarize_sheets_cache(cache: dict) -> list[dict]:
    rows: list[dict] = []
    if not isinstance(cache, dict):
        return rows
    for key, value in cache.items():
        if isinstance(value, dict):
            rows.append(
                {
                    "name": key,
                    "count": value.get("count", value.get("items", "—")),
                    "dirty": value.get("dirty", value.get("dirty_count", 0)),
                    "last_sync": value.get("last_sync", value.get("updated", "—")),
                }
            )
        else:
            rows.append({"name": key, "count": value, "dirty": "—", "last_sync": "—"})
    return rows


def _panel_staff_users():
    return (
        User.objects.filter(groups__name__in=[GROUP_OPERATOR, GROUP_ADMIN])
        .distinct()
        .prefetch_related("groups")
        .order_by("username")
    )


def _get_panel_user(user_id: int) -> User:
    user = User.objects.filter(pk=user_id).first()
    if not user or not user.groups.filter(
        name__in=[GROUP_OPERATOR, GROUP_ADMIN]
    ).exists():
        if not (user and user.is_superuser):
            raise Http404("Usuario del panel no encontrado")
    return user


def _panel_role_for_user(user: User) -> str:
    if user.groups.filter(name=GROUP_ADMIN).exists() or user.is_superuser:
        return PanelStaffForm.ROLE_ADMIN
    return PanelStaffForm.ROLE_OPERATOR


def _apply_panel_role(user: User, role: str) -> None:
    operator_group, _ = Group.objects.get_or_create(name=GROUP_OPERATOR)
    admin_group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)
    user.groups.remove(operator_group, admin_group)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    if role == PanelStaffForm.ROLE_ADMIN:
        user.groups.add(admin_group, operator_group)
    else:
        user.groups.add(operator_group)
