from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.filesync.models import StoredFile
from apps.imports.models import ImportJob
from apps.imports.registry import get_importer


@staff_member_required
@require_POST
def import_file(request, file_id):
    stored_file = get_object_or_404(StoredFile.objects.select_related("data_source", "submodule__module"), id=file_id)
    replace = request.POST.get("replace") == "1"
    parser_key = stored_file.data_source.parser_key if stored_file.data_source else ""
    importer_class = get_importer(parser_key)
    job = importer_class(stored_file, user=request.user, replace=replace).run()
    if job.status == ImportJob.STATUS_SUCCESS:
        messages.success(request, f"Imported {job.rows_imported} rows from {stored_file.original_name}.")
    elif job.status == ImportJob.STATUS_SKIPPED:
        messages.error(request, job.error_message)
    else:
        messages.error(request, f"Import failed: {job.error_message}")
    return redirect("imports:import_detail", job_id=job.id)


@staff_member_required
def import_detail(request, job_id):
    job = get_object_or_404(ImportJob.objects.select_related("stored_file", "submodule__module"), id=job_id)
    return render(request, "imports/import_detail.html", {"job": job})

# Create your views here.
