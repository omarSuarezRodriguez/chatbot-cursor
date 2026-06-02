from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path("health", lambda _request: JsonResponse({"status": "ok", "service": "dashboard"})),
    path("health/", lambda _request: JsonResponse({"status": "ok", "service": "dashboard"})),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.operations.urls")),
]
