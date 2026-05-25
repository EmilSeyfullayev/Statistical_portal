from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.shortcuts import render

from apps.analytics.models import InteractionEvent
from apps.reports.models import ReportDownload


@staff_member_required
def statistics(request):
    events = InteractionEvent.objects.select_related("user", "module", "submodule", "dashboard", "report")
    downloads = ReportDownload.objects.select_related("user", "module", "submodule", "report")
    context = {
        "recent_events": events[:50],
        "recent_downloads": downloads[:50],
        "top_modules": events.filter(module__isnull=False)
        .values("module__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10],
        "top_submodules": events.filter(submodule__isnull=False)
        .values("submodule__name", "module__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10],
        "top_reports": events.filter(report__isnull=False)
        .values("report__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10],
    }
    return render(request, "analytics/statistics.html", context)

# Create your views here.
