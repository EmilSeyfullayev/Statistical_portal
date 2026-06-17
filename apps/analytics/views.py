from collections import Counter

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date

from apps.accounts.decorators import admin_required
from apps.analytics.models import InteractionEvent
from apps.analytics.services import record_interaction
from apps.catalog.models import Submodule
from apps.reports.models import ReportDownload


def display_user_name(user):
    if not user:
        return "-"
    full_name = user.get_full_name().strip()
    return f"{full_name} ({user.username})" if full_name else user.username


def metadata_value(metadata, key):
    value = metadata.get(key, "")
    return value if value not in (None, "") else "-"


def display_language(metadata):
    labels = {"az": "Azərbaycan", "en": "English", "ru": "Русский"}
    language = metadata.get("language", "")
    return labels.get(language, language or "-")


@require_POST
def track_report_language(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False}, status=403)
    submodule = get_object_or_404(
        Submodule.objects.select_related("module"),
        module__slug=request.POST.get("module_slug"),
        slug=request.POST.get("submodule_slug"),
        is_active=True,
    )
    language = request.POST.get("language", "az")
    record_interaction(
        request,
        InteractionEvent.REPORT_PREVIEW,
        module=submodule.module,
        submodule=submodule,
        target_url=request.POST.get("target_url") or request.path,
        metadata={
            "action": "language_tab",
            "report_name": request.POST.get("report_name", "-"),
            "report_number": request.POST.get("report_number", ""),
            "language": language,
            "month": request.POST.get("month", ""),
            "country": request.POST.get("country", ""),
        },
    )
    return JsonResponse({"ok": True})


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
        event.display_language = display_language(event.request_metadata)
        event.display_report_number = metadata_value(event.request_metadata, "report_number")
        event.display_month = metadata_value(event.request_metadata, "month")
        event.display_country = metadata_value(event.request_metadata, "country")
    recent_downloads = list(downloads[:50])
    for download in recent_downloads:
        download.display_user_name = display_user_name(download.user)
        download.display_report_name = (
            str(download.report) if download.report else download.request_metadata.get("report_name", "-")
        )
        download.display_language = display_language(download.request_metadata)
        download.display_report_number = metadata_value(download.request_metadata, "report_number")
        download.display_month = metadata_value(download.request_metadata, "month")
        download.display_country = metadata_value(download.request_metadata, "country")
    download_counter = Counter()
    for download in downloads:
        report_name = download.report.name if download.report else download.request_metadata.get("report_name", "-")
        report_format = download.format
        language = display_language(download.request_metadata)
        download_counter[(report_name, report_format, language)] += 1
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
            {"report_name": report_name, "format": report_format, "language": language, "total": total}
            for (report_name, report_format, language), total in download_counter.most_common(10)
        ],
    }
    return render(request, "analytics/statistics.html", context)

# Create your views here.
