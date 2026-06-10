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
    get_transit_download_rows,
    get_transit_dashboard_context,
    get_transit_dynamics_report_context,
    get_transit_merged_context,
    get_transit_portal_context,
    get_transit_portal_download_rows,
)
from apps.reports.models import ReportDownload


TRANSIT_DYNAMICS_REPORT_NAME = "Azərbaycan Üzərindən Tranzit Rejimdə Daşınmış Yüklərin Dinamika Hesabatı"


def record_transit_dynamics_download(request, submodule, report_context, report_format, filename):
    metadata = {
        "report_name": TRANSIT_DYNAMICS_REPORT_NAME,
        "report_number": report_context["report_number"],
        "format": report_format,
        "filename": filename,
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
    elif submodule.module.slug == "processed-data" and submodule.slug == "transit":
        transit_table = {
            "context_loader": get_transit_portal_context,
            "download_loader": get_transit_portal_download_rows,
            "sheet_title": "Transit Portal",
            "filename": "transit_data_for_portal.xlsx",
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
        transit_dynamics_report = get_transit_dynamics_report_context()
        if transit_dynamics_report.get("available"):
            filename_base = transit_dynamics_report["report_number"].replace("/", "-")
            if request.GET.get("download") == "docx":
                output = build_transit_dynamics_report_docx(transit_dynamics_report)
                filename = f"{filename_base}.docx"
                record_transit_dynamics_download(request, submodule, transit_dynamics_report, "docx", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            if request.GET.get("download") == "pdf":
                output = build_transit_dynamics_report_pdf(transit_dynamics_report)
                filename = f"{filename_base}.pdf"
                record_transit_dynamics_download(request, submodule, transit_dynamics_report, "pdf", filename)
                return FileResponse(
                    output,
                    as_attachment=True,
                    filename=filename,
                    content_type="application/pdf",
                )
        context["transit_dynamics_report"] = transit_dynamics_report
    return render(request, "dashboard/submodule_detail.html", context)

# Create your views here.
