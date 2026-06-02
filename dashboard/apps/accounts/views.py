from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views import View

from apps.accounts.audit import log_audit
from apps.accounts.models import AuditLog
from apps.operations.permissions import AdminRequiredMixin

AUDIT_PER_PAGE = 25


class AuditListView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request):
        action = request.GET.get("action", "").strip()
        entity = request.GET.get("entity", "").strip()
        user_q = request.GET.get("user", "").strip()
        try:
            page_num = max(1, int(request.GET.get("page", "1")))
        except ValueError:
            page_num = 1

        qs = AuditLog.objects.select_related("user").all()
        if action:
            qs = qs.filter(action__icontains=action)
        if entity:
            qs = qs.filter(entity__icontains=entity)
        if user_q:
            qs = qs.filter(user__username__icontains=user_q)

        paginator = Paginator(qs, AUDIT_PER_PAGE)
        page_obj = paginator.get_page(page_num)

        log_audit(
            request,
            action="view",
            entity="audit_log",
            metadata={"action_filter": action or None, "entity_filter": entity or None},
        )

        query_params = request.GET.copy()
        query_params.pop("page", None)
        base_query = query_params.urlencode()

        return render(
            request,
            "accounts/audit_list.html",
            {
                "page_obj": page_obj,
                "entries": page_obj.object_list,
                "action_filter": action,
                "entity_filter": entity,
                "user_filter": user_q,
                "base_query": base_query,
            },
        )
