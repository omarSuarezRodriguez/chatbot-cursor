from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path

urlpatterns = [
    path("", lambda request: redirect("operations:home", permanent=False)),
    path("health", lambda _request: JsonResponse({"status": "ok", "service": "dashboard"})),
    path("health/", lambda _request: JsonResponse({"status": "ok", "service": "dashboard"})),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="root_login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="root_logout"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("mipanel/", include("apps.operations.urls")),
]
