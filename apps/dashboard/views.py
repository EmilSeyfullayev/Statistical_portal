from openpyxl import Workbook

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.analytics.models import InteractionEvent
from apps.analytics.services import record_interaction
from apps.catalog.models import DashboardDefinition, Module, Submodule
from apps.dashboard.services import (
    get_transit_download_rows,
    get_transit_dashboard_context,
    get_transit_dynamics_report_context,
    get_transit_merged_context,
    get_transit_portal_context,
    get_transit_portal_download_rows,
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
        context["transit_dynamics_report"] = get_transit_dynamics_report_context()
    return render(request, "dashboard/submodule_detail.html", context)

# Create your views here.
