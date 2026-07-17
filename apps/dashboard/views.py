from openpyxl import Workbook

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.analytics.models import InteractionEvent
from apps.analytics.services import record_interaction
from apps.catalog.models import DashboardDefinition, Module, Submodule
from apps.dashboard.services import (
    build_transit_dynamics_report_docx,
    build_transit_dynamics_report_pdf,
    get_foreign_trucks_context,
    get_foreign_trucks_download_rows,
    get_local_trucks_context,
    get_local_trucks_download_rows,
    get_processed_trucks_context,
    get_processed_trucks_download_rows,
    get_transit_download_rows,
    get_transit_corridor_report_context,
    get_transit_corridor_report_contexts,
    get_transit_country_report_context,
    get_transit_country_report_contexts,
    get_transit_dashboard_context,
    get_transit_dynamics_report_context,
    get_transit_dynamics_report_contexts,
    get_transit_merged_context,
    get_transit_portal_context,
    get_transit_portal_download_rows,
    get_transit_posts_report_context,
    get_transit_posts_report_contexts,
)
from apps.reports.models import ReportDownload


TRANSIT_DYNAMICS_REPORT_NAME = "Azərbaycan Üzərindən Tranzit Rejimdə Daşınmış Yüklərin Dinamika Hesabatı"
TRANSIT_DYNAMICS_LANGUAGE_SUFFIXES = {"az": "AZ", "en": "EN", "ru": "RU"}
TRANSIT_DYNAMICS_MONTH_NAMES = {
    1: "Yanvar",
    2: "Fevral",
    3: "Mart",
    4: "Aprel",
    5: "May",
    6: "İyun",
    7: "İyul",
    8: "Avqust",
    9: "Sentyabr",
    10: "Oktyabr",
    11: "Noyabr",
    12: "Dekabr",
}



def month_options(max_month, selected_month):
    return [
        {"value": month, "label": TRANSIT_DYNAMICS_MONTH_NAMES[month], "selected": month == selected_month}
        for month in range(1, max_month + 1)
    ]


def selected_report_month(request):
    try:
        return int(request.GET.get("month", ""))
    except ValueError:
        return None
TRANSIT_DYNAMICS_LANGUAGE_OPTIONS = [
    {"code": "az", "label": "Azərbaycan"},
    {"code": "en", "label": "English"},
    {"code": "ru", "label": "Русский"},
]


def record_transit_dynamics_download(request, submodule, report_context, report_format, filename):
    metadata = {
        "report_name": report_context.get("text", {}).get("title", TRANSIT_DYNAMICS_REPORT_NAME),
        "report_number": report_context["report_number"],
        "format": report_format,
        "filename": filename,
        "language": report_context.get("language", "az"),
        "month": report_context.get("selected_month", ""),
        "country": report_context.get("selected_country", ""),
        "corridor": report_context.get("selected_corridor", ""),
    }
    record_interaction(
        request,
        InteractionEvent.REPORT_LINK_CLICK,
        module=submodule.module,
        submodule=submodule,
        target_url=request.get_full_path(),
        metadata=metadata,
    )
    ReportDownload.objects.create(
        user=request.user if request.user.is_authenticated else None,
        report=None,
        module=submodule.module,
        submodule=submodule,
        format=report_format,
        generated_file_path=filename,
        request_metadata=metadata,
    )


@login_required
def home(request):
    dashboards = DashboardDefinition.objects.filter(is_active=True)
    modules = Module.objects.filter(is_active=True).prefetch_related("submodules", "dashboards")
    record_interaction(request, InteractionEvent.DASHBOARD_VIEW, target_url=request.path)
    return render(request, "dashboard/home.html", {"dashboards": dashboards, "modules": modules})


@login_required
def dashboard_detail(request, dashboard_slug):
    dashboard = get_object_or_404(DashboardDefinition, slug=dashboard_slug, is_active=True)
    record_interaction(request, InteractionEvent.DASHBOARD_VIEW, dashboard=dashboard)
    context = {"dashboard": dashboard}
    if dashboard.slug == "transit":
        context["transit_dashboard"] = get_transit_dashboard_context(request.GET)
    return render(request, "dashboard/dashboard_detail.html", context)


@login_required
def module_detail(request, module_slug):
    module = get_object_or_404(Module.objects.prefetch_related("submodules"), slug=module_slug, is_active=True)
    record_interaction(request, InteractionEvent.MODULE_VIEW, module=module)
    return render(request, "dashboard/module_detail.html", {"module": module})


@login_required
def submodule_detail(request, module_slug, submodule_slug):
    submodule = get_object_or_404(
        Submodule.objects.select_related("module").prefetch_related("reports", "data_sources"),
        module__slug=module_slug,
        slug=submodule_slug,
        is_active=True,
    )
    if not request.GET.get("download"):
        record_interaction(
            request,
            InteractionEvent.SUBMODULE_VIEW,
            module=submodule.module,
            submodule=submodule,
        )
    context = {"submodule": submodule}
    transit_table = None
    if submodule.module.slug == "datalar" and submodule.slug == "tranzit":
        transit_table = {
            "context_loader": get_transit_merged_context,
            "download_loader": get_transit_download_rows,
            "sheet_title": "Transit",
            "filename": "transit_merged.xlsx",
        }
    elif submodule.module.slug == "datalar" and submodule.slug == "xarici-tir-lar":
        transit_table = {
            "context_loader": get_foreign_trucks_context,
            "download_loader": get_foreign_trucks_download_rows,
            "sheet_title": "Foreign Trucks",
            "filename": "foreign_trucks.xlsx",
        }
    elif submodule.module.slug == "datalar" and submodule.slug == "yerli-tir-lar":
        transit_table = {
            "context_loader": get_local_trucks_context,
            "download_loader": get_local_trucks_download_rows,
            "sheet_title": "Local Trucks",
            "filename": "local_trucks.xlsx",
        }
    elif submodule.module.slug == "processed-data" and submodule.slug == "transit":
        transit_table = {
            "context_loader": get_transit_portal_context,
            "download_loader": get_transit_portal_download_rows,
            "sheet_title": "Transit Portal",
            "filename": "transit_data_for_portal.xlsx",
        }
    elif submodule.module.slug == "processed-data" and submodule.slug == "tir-lar":
        transit_table = {
            "context_loader": get_processed_trucks_context,
            "download_loader": get_processed_trucks_download_rows,
            "sheet_title": "TIR Portal",
            "filename": "trucks_aggregated.xlsx",
        }

    if transit_table:
        if request.GET.get("download") == "xlsx":
            headers, rows = transit_table["download_loader"](request.GET)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = transit_table["sheet_title"]
            sheet.append(headers)
            for row in rows:
                sheet.append(row)
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = f'attachment; filename="{transit_table["filename"]}"'
            workbook.save(response)
            return response
        context["transit_data"] = transit_table["context_loader"](request.GET)
    elif submodule.module.slug == "tranzit-daşımalar" and submodule.slug == "dinamika-arayışı":
        context["transit_dynamics_language_options"] = TRANSIT_DYNAMICS_LANGUAGE_OPTIONS
        selected_month = selected_report_month(request)
        transit_dynamics_report = get_transit_dynamics_report_context(selected_month=selected_month)
        transit_dynamics_reports = get_transit_dynamics_report_contexts(transit_dynamics_report)
        reports_by_language = {report["language"]: report for report in transit_dynamics_reports}

        if transit_dynamics_report.get("available"):
            selected_month = transit_dynamics_report["selected_month"]
            max_month = transit_dynamics_report["max_month"]
            context["transit_dynamics_selected_month"] = selected_month
            context["transit_dynamics_month_options"] = month_options(max_month, selected_month)
            language = request.GET.get("lang", "az")
            if language not in reports_by_language:
                language = "az"
            download_report = reports_by_language[language]
            filename_base = transit_dynamics_report["report_number"].replace("/", "-")
            language_suffix = TRANSIT_DYNAMICS_LANGUAGE_SUFFIXES[language]
            if request.GET.get("download") == "docx":
                output = build_transit_dynamics_report_docx(download_report)
                filename = f"{filename_base}-{language_suffix}.docx"
                record_transit_dynamics_download(request, submodule, download_report, "docx", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            if request.GET.get("download") == "pdf":
                output = build_transit_dynamics_report_pdf(download_report)
                filename = f"{filename_base}-{language_suffix}.pdf"
                record_transit_dynamics_download(request, submodule, download_report, "pdf", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/pdf",
                )
        context["transit_dynamics_report"] = transit_dynamics_report
        context["transit_dynamics_reports"] = transit_dynamics_reports
    elif submodule.module.slug == "tranzit-daşımalar" and submodule.slug == "ölkələr-üzrə-arayış":
        context["transit_dynamics_language_options"] = TRANSIT_DYNAMICS_LANGUAGE_OPTIONS
        selected_month = selected_report_month(request)
        selected_country = request.GET.get("country") or None
        country_report = get_transit_country_report_context(
            selected_month=selected_month,
            selected_country=selected_country,
        )
        country_reports = get_transit_country_report_contexts(country_report)
        reports_by_language = {report["language"]: report for report in country_reports}

        if country_report.get("available"):
            selected_month = country_report["selected_month"]
            selected_country = country_report["selected_country"]
            context["transit_dynamics_selected_month"] = selected_month
            context["transit_dynamics_month_options"] = month_options(country_report["max_month"], selected_month)
            context["transit_country_selected"] = selected_country
            context["transit_country_options"] = [
                {"value": country, "selected": country == selected_country}
                for country in country_report["country_options"]
            ]
            language = request.GET.get("lang", "az")
            if language not in reports_by_language:
                language = "az"
            download_report = reports_by_language[language]
            filename_base = country_report["report_number"].replace("/", "-")
            language_suffix = TRANSIT_DYNAMICS_LANGUAGE_SUFFIXES[language]
            if request.GET.get("download") == "docx":
                output = build_transit_dynamics_report_docx(download_report)
                filename = f"{filename_base}-{language_suffix}.docx"
                record_transit_dynamics_download(request, submodule, download_report, "docx", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            if request.GET.get("download") == "pdf":
                output = build_transit_dynamics_report_pdf(download_report)
                filename = f"{filename_base}-{language_suffix}.pdf"
                record_transit_dynamics_download(request, submodule, download_report, "pdf", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/pdf",
                )
        context["transit_dynamics_report"] = country_report
        context["transit_dynamics_reports"] = country_reports
    elif submodule.module.slug == "tranzit-daşımalar" and submodule.slug == "dəhlizlər-üzrə-arayış":
        context["transit_dynamics_language_options"] = TRANSIT_DYNAMICS_LANGUAGE_OPTIONS
        selected_month = selected_report_month(request)
        selected_corridor = request.GET.get("corridor") or None
        corridor_report = get_transit_corridor_report_context(
            selected_month=selected_month,
            selected_corridor=selected_corridor,
        )
        corridor_reports = get_transit_corridor_report_contexts(corridor_report)
        reports_by_language = {report["language"]: report for report in corridor_reports}

        if corridor_report.get("available"):
            selected_month = corridor_report["selected_month"]
            selected_corridor = corridor_report["selected_corridor"]
            context["transit_dynamics_selected_month"] = selected_month
            context["transit_dynamics_month_options"] = month_options(corridor_report["max_month"], selected_month)
            context["transit_corridor_selected"] = selected_corridor
            context["transit_corridor_options"] = [
                {"value": corridor, "selected": corridor == selected_corridor}
                for corridor in corridor_report["corridor_options"]
            ]
            language = request.GET.get("lang", "az")
            if language not in reports_by_language:
                language = "az"
            download_report = reports_by_language[language]
            filename_base = corridor_report["report_number"].replace("/", "-")
            language_suffix = TRANSIT_DYNAMICS_LANGUAGE_SUFFIXES[language]
            if request.GET.get("download") == "docx":
                output = build_transit_dynamics_report_docx(download_report)
                filename = f"{filename_base}-{language_suffix}.docx"
                record_transit_dynamics_download(request, submodule, download_report, "docx", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            if request.GET.get("download") == "pdf":
                output = build_transit_dynamics_report_pdf(download_report)
                filename = f"{filename_base}-{language_suffix}.pdf"
                record_transit_dynamics_download(request, submodule, download_report, "pdf", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/pdf",
                )
        context["transit_dynamics_report"] = corridor_report
        context["transit_dynamics_reports"] = corridor_reports
    elif submodule.module.slug == "tranzit-daşımalar" and submodule.slug == "postlar-üzrə-arayış":
        context["transit_dynamics_language_options"] = TRANSIT_DYNAMICS_LANGUAGE_OPTIONS
        selected_month = selected_report_month(request)
        posts_report = get_transit_posts_report_context(selected_month=selected_month)
        posts_reports = get_transit_posts_report_contexts(posts_report)
        reports_by_language = {report["language"]: report for report in posts_reports}

        if posts_report.get("available"):
            selected_month = posts_report["selected_month"]
            context["transit_dynamics_selected_month"] = selected_month
            context["transit_dynamics_month_options"] = month_options(posts_report["max_month"], selected_month)
            language = request.GET.get("lang", "az")
            if language not in reports_by_language:
                language = "az"
            download_report = reports_by_language[language]
            filename_base = posts_report["report_number"].replace("/", "-")
            language_suffix = TRANSIT_DYNAMICS_LANGUAGE_SUFFIXES[language]
            if request.GET.get("download") == "docx":
                output = build_transit_dynamics_report_docx(download_report)
                filename = f"{filename_base}-{language_suffix}.docx"
                record_transit_dynamics_download(request, submodule, download_report, "docx", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            if request.GET.get("download") == "pdf":
                output = build_transit_dynamics_report_pdf(download_report)
                filename = f"{filename_base}-{language_suffix}.pdf"
                record_transit_dynamics_download(request, submodule, download_report, "pdf", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/pdf",
                )
        context["transit_dynamics_report"] = posts_reports[0] if posts_reports else posts_report
        context["transit_dynamics_reports"] = posts_reports
    return render(request, "dashboard/submodule_detail.html", context)

# Create your views here.
