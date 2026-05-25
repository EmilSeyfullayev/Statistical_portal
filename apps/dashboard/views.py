from openpyxl import Workbook

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.analytics.models import InteractionEvent
from apps.analytics.services import record_interaction
from apps.catalog.models import DashboardDefinition, Module, Submodule
from apps.dashboard.services import get_transit_download_rows, get_transit_merged_context


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
    return render(request, "dashboard/dashboard_detail.html", {"dashboard": dashboard})


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
    if submodule.module.slug == "datalar" and submodule.slug == "tranzit":
        if request.GET.get("download") == "xlsx":
            headers, rows = get_transit_download_rows(request.GET)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Transit"
            sheet.append(headers)
            for row in rows:
                sheet.append(row)
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="transit_merged.xlsx"'
            workbook.save(response)
            return response
        context["transit_data"] = get_transit_merged_context(request.GET)
    return render(request, "dashboard/submodule_detail.html", context)

# Create your views here.
