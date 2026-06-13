import json
from datetime import date, timedelta

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.template.response import TemplateResponse

from .models import SyncLog


def get_chart_data() -> dict:
    thirty_days_ago = date.today() - timedelta(days=29)

    status_data = SyncLog.objects.values("success").annotate(count=Count("id"))
    success_count = next((x["count"] for x in status_data if x["success"]), 0)
    error_count = next((x["count"] for x in status_data if not x["success"]), 0)

    daily = (
        SyncLog.objects.filter(sync_time__date__gte=thirty_days_ago)
        .annotate(date=TruncDate("sync_time"))
        .values("date", "success")
        .annotate(count=Count("id"), total_amount=Sum("transaction_amount"))
        .order_by("date")
    )

    all_dates = [str(thirty_days_ago + timedelta(days=i)) for i in range(30)]
    daily_success = {str(r["date"]): r["count"] for r in daily if r["success"]}
    daily_error = {str(r["date"]): r["count"] for r in daily if not r["success"]}
    daily_amount: dict = {}
    for r in daily:
        d = str(r["date"])
        daily_amount[d] = daily_amount.get(d, 0) + float(r["total_amount"] or 0)

    return {
        "chart_success_count": success_count,
        "chart_error_count": error_count,
        "chart_dates": json.dumps(all_dates),
        "chart_daily_success": json.dumps([daily_success.get(d, 0) for d in all_dates]),
        "chart_daily_error": json.dumps([daily_error.get(d, 0) for d in all_dates]),
        "chart_daily_amount": json.dumps([daily_amount.get(d, 0) for d in all_dates]),
    }


def dashboard_callback(request, context):
    context.update(get_chart_data())
    context["recent_logs"] = (
        SyncLog.objects.select_related("bank_mail", "bank_mail__bank_account")
        .order_by("-sync_time")[:20]
    )
    return context


@staff_member_required
def recent_actions_view(request):
    log_entries = (
        LogEntry.objects.select_related("user", "content_type")
        .order_by("-action_time")[:100]
    )
    context = {
        **admin.site.each_context(request),
        "title": "Recent Actions",
        "subtitle": None,
        "log_entries": log_entries,
    }
    return TemplateResponse(request, "admin/mailsync/recent_actions.html", context)
