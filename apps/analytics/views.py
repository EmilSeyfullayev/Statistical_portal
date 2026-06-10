from collections import Counter

from django.db.models import Count
from django.shortcuts import render
from django.utils.dateparse import parse_date

from apps.accounts.decorators import admin_required
from apps.analytics.models import InteractionEvent
from apps.reports.models import ReportDownload


def display_user_name(user):
    if not user:
        return "-"
    full_name = user.get_full_name().strip()
    return f"{full_name} ({user.username})" if full_name else user.username


@admin_required
def statistics(request):
    events = InteractionEvent.objects.select_related("user", "module", "submodule", "dashboard", "report")
    downloads = ReportDownload.objects.select_related("user", "module", "submodule", "report")
    start_date = parse_date(request.GET.get("start_date") or "")
    end_date = parse_date(request.GET.get("end_date") or "")
    if start_date:
        events = events.filter(created_at__date__gte=start_date)
        downloads = downloads.filter(downloaded_at__date__gte=start_date)
    if end_date:
        events = events.filter(created_at__date__lte=end_date)
        downloads = downloads.filter(downloaded_at__date__lte=end_date)

    visible_events = events.exclude(event_type=InteractionEvent.REPORT_DOWNLOAD_START)
    recent_events = list(visible_events[:50])
    for event in recent_events:
        event.display_user_name = display_user_name(event.user)
        event.display_report_name = event.report.name if event.report else event.request_metadata.get("report_name", "-")
        event.display_format = event.request_metadata.get("format", "-")
    recent_downloads = list(downloads[:50])
    for download in recent_downloads:
        download.display_user_name = display_user_name(download.user)
        download.display_report_name = (
            str(download.report) if download.report else download.request_metadata.get("report_name", "-")
        )
    download_counter = Counter()
    for download in downloads:
        report_name = download.report.name if download.report else download.request_metadata.get("report_name", "-")
        report_format = download.format
        download_counter[(report_name, report_format)] += 1
    context = {
        "recent_events": recent_events,
        "recent_downloads": recent_downloads,
        "filter_start_date": request.GET.get("start_date", ""),
        "filter_end_date": request.GET.get("end_date", ""),
        "top_modules": visible_events.filter(module__isnull=False)
        .values("module__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10],
        "top_submodules": visible_events.filter(submodule__isnull=False)
        .values("submodule__name", "module__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10],
        "top_download_events": [
            {"report_name": report_name, "format": report_format, "total": total}
            for (report_name, report_format), total in download_counter.most_common(10)
        ],
    }
    return render(request, "analytics/statistics.html", context)

# Create your views here.
