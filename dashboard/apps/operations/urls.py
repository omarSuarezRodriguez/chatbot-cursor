from django.urls import path

from . import views

app_name = "operations"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("dashboard/", views.DashboardHomeView.as_view(), name="dashboard"),
    path("pedidos/", views.OrderListView.as_view(), name="orders"),
    path("pedidos/nuevo/", views.OrderCreateView.as_view(), name="order_create"),
    path("pedidos/<str:order_id>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("reservas/", views.ReservationListView.as_view(), name="reservations"),
    path(
        "reservas/<str:reservation_id>/",
        views.ReservationDetailView.as_view(),
        name="reservation_detail",
    ),
    path("administracion/", views.AdminHubView.as_view(), name="admin_hub"),
    path("administracion/escrituras/", views.WritesHelpView.as_view(), name="writes_help"),
    path(
        "administracion/accesos/",
        views.PanelStaffListView.as_view(),
        name="panel_staff_list",
    ),
    path(
        "administracion/accesos/nuevo/",
        views.PanelStaffCreateView.as_view(),
        name="panel_staff_create",
    ),
    path(
        "administracion/accesos/<int:user_id>/editar/",
        views.PanelStaffEditView.as_view(),
        name="panel_staff_edit",
    ),
    path("menu/", views.MenuView.as_view(), name="menu"),
    path("menu/nuevo/", views.MenuItemCreateView.as_view(), name="menu_create"),
    path("menu/<str:item_id>/editar/", views.MenuItemEditView.as_view(), name="menu_edit"),
    path("menu/<str:item_id>/eliminar/", views.MenuItemDeleteView.as_view(), name="menu_delete"),
    path("usuarios/", views.UserListView.as_view(), name="users"),
    path("usuarios/nuevo/", views.CustomerCreateView.as_view(), name="customer_create"),
    path("usuarios/<str:wa_id>/", views.CustomerDetailView.as_view(), name="customer_detail"),
    path("usuarios/<str:wa_id>/editar/", views.CustomerEditView.as_view(), name="customer_edit"),
    path("usuarios/<str:wa_id>/eliminar/", views.CustomerDeleteView.as_view(), name="customer_delete"),
    path("configuracion/", views.PanelSettingsView.as_view(), name="panel_settings"),
    path("estado/", views.SystemStatusView.as_view(), name="system_status"),
]
