from django.urls import path

from . import views

app_name = "operations"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("dashboard/", views.DashboardHomeView.as_view(), name="dashboard"),
    path("pedidos/", views.OrderListView.as_view(), name="orders"),
    path("pedidos/<str:order_id>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("reservas/", views.ReservationListView.as_view(), name="reservations"),
    path("menu/", views.MenuView.as_view(), name="menu"),
    path("usuarios/", views.UserListView.as_view(), name="users"),
    path("estado/", views.SystemStatusView.as_view(), name="system_status"),
]
