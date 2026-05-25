from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from apps.analytics.models import InteractionEvent
from apps.analytics.services import record_interaction
from apps.reports.models import ReportDefinition
from apps.reports.services import generate_report_file, record_download

CONTENT_TYPES = {
    ReportDefinition.FORMAT_DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ReportDefinition.FORMAT_PDF: "application/pdf",
}


@login_required
def download(request, report_id):
    report = get_object_or_404(
        ReportDefinition.objects.select_related("submodule__module"),
        id=report_id,
        is_active=True,
    )
    record_interaction(
        request,
        InteractionEvent.REPORT_LINK_CLICK,
        module=report.submodule.module,
        submodule=report.submodule,
        report=report,
    )
    record_interaction(
        request,
        InteractionEvent.REPORT_DOWNLOAD_START,
        module=report.submodule.module,
        submodule=report.submodule,
        report=report,
    )
    output_path = generate_report_file(report)
    record_download(request, report, output_path)
    return FileResponse(
        open(output_path, "rb"),
        as_attachment=True,
        filename=output_path.name,
        content_type=CONTENT_TYPES.get(report.format, "application/octet-stream"),
    )

# Create your views here.
