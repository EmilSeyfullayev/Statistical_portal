from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import DataSource
from apps.filesync.models import SyncJob
from apps.filesync.services import synchronize_data_source


@staff_member_required
@require_POST
def sync_source(request, source_id):
    data_source = get_object_or_404(DataSource.objects.select_related("submodule__module"), id=source_id)
    sync_job = synchronize_data_source(data_source, request.user)
    if sync_job.status == SyncJob.STATUS_SUCCESS:
        messages.success(
            request,
            f"Sync completed: {sync_job.files_uploaded} uploaded, {sync_job.files_existing} existing.",
        )
    else:
        messages.error(request, f"Sync failed: {sync_job.error_message}")
    return redirect("filesync:sync_detail", job_id=sync_job.id)


@staff_member_required
def sync_detail(request, job_id):
    sync_job = get_object_or_404(SyncJob.objects.select_related("data_source"), id=job_id)
    return render(request, "filesync/sync_detail.html", {"sync_job": sync_job})

# Create your views here.
