"""Critical dashboard view tests (filters, permissions, bot_bridge mocked)."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import AuditLog
from apps.accounts.views import AuditListView
from apps.operations.permissions import GROUP_ADMIN, GROUP_OPERATOR
from apps.operations.views import (
    OrderCreateView,
    OrderListView,
    PanelStaffListView,
    SystemStatusView,
    WritesHelpView,
)
from services.bot_bridge import WriteResult


class DashboardViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()
        operator_group, _ = Group.objects.get_or_create(name=GROUP_OPERATOR)
        admin_group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)
        self.operator = User.objects.create_user("op", password="testpass123")
        self.operator.groups.add(operator_group)
        self.admin = User.objects.create_user("adm", password="testpass123")
        self.admin.groups.add(admin_group, operator_group)
        self.guest = User.objects.create_user("guest", password="testpass123")

    def _get(self, view_cls, path: str, user: User | None = None, data: dict | None = None):
        request = self.factory.get(path, data or {})
        if user:
            request.user = user
        else:
            from django.contrib.auth.models import AnonymousUser

            request.user = AnonymousUser()
        return view_cls.as_view()(request)

    def test_login_required_orders(self):
        response = self._get(OrderListView, "/pedidos/")
        self.assertEqual(response.status_code, 302)

    @patch("apps.operations.views.readers.query_orders")
    def test_order_list_status_filter(self, mock_query):
        mock_query.return_value = [
            {
                "order_id": "ORD-1",
                "customer_name": "Ana",
                "total": 10,
                "status": "pending",
                "timestamp": "2026-01-01T12:00:00",
            }
        ]
        response = self._get(
            OrderListView, "/pedidos/", user=self.operator, data={"status": "pending"}
        )
        self.assertEqual(response.status_code, 200)
        mock_query.assert_called_once()
        self.assertEqual(mock_query.call_args.kwargs.get("status"), "pending")
        self.assertIn(b"ORD-1", response.content)

    def test_audit_requires_admin(self):
        with self.assertRaises(PermissionDenied):
            self._get(AuditListView, "/accounts/audit/", user=self.operator)

    def test_audit_list_admin(self):
        AuditLog.objects.create(action="view", entity="orders", user=self.admin)
        response = self._get(AuditListView, "/accounts/audit/", user=self.admin)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"orders", response.content)

    @patch("apps.operations.views.bot_bridge.writes_enabled", return_value=False)
    def test_order_create_get_operator(self, _mock_writes):
        response = self._get(OrderCreateView, "/pedidos/nuevo/", user=self.operator)
        self.assertEqual(response.status_code, 200)

    @patch("apps.operations.views.bot_bridge.create_manual_order")
    @patch("apps.operations.views.bot_bridge.writes_enabled", return_value=True)
    def test_order_create_post_calls_bridge(self, _enabled, mock_create):
        mock_create.return_value = WriteResult(
            ok=True, message="OK", entity_id="ORD-NEW"
        )
        self.client.login(username="op", password="testpass123")
        response = self.client.post(
            reverse("operations:order_create"),
            {
                "wa_id": "34600000000",
                "customer_name": "Test",
                "items_json": '[{"product":"Pizza","qty":1,"unit_price":10}]',
            },
        )
        self.assertEqual(response.status_code, 302)
        mock_create.assert_called_once()

    @patch("apps.operations.views.readers.sheets_cache_status", return_value={"menu": {"count": 1}})
    @patch("apps.operations.views._fetch_bot_health")
    def test_system_status_renders(self, mock_health, _cache):
        mock_health.return_value = (
            {"status": "ok", "restaurant": "Demo", "admin_configured": True},
            "",
        )
        response = self._get(SystemStatusView, "/estado/", user=self.guest)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"En l\xc3\xadnea", response.content)

    def test_panel_staff_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self._get(PanelStaffListView, "/administracion/accesos/", user=self.operator)
        response = self._get(PanelStaffListView, "/administracion/accesos/", user=self.admin)
        self.assertEqual(response.status_code, 200)

    @patch("apps.operations.views.bot_bridge.confirm_order")
    @patch("apps.operations.views.bot_bridge.writes_enabled", return_value=True)
    @patch("apps.operations.views.readers.read_order")
    def test_order_confirm_post(self, mock_read, _writes, mock_confirm):
        mock_read.return_value = {
            "order_id": "ORD-X",
            "status": "pending",
            "items": [],
        }
        mock_confirm.return_value = WriteResult(ok=True, message="Confirmado")
        self.client.login(username="op", password="testpass123")
        response = self.client.post(
            reverse("operations:order_detail", kwargs={"order_id": "ORD-X"}),
            {"action": "confirm"},
        )
        self.assertEqual(response.status_code, 302)
        mock_confirm.assert_called_once_with("ORD-X")

    def test_writes_help_accessible(self):
        response = self._get(WritesHelpView, "/administracion/escrituras/", user=self.guest)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DASHBOARD_ENABLE_WRITES", response.content)
