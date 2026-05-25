import hashlib
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.filesync.models import StoredFile, SyncJob, SyncJobFile


def file_checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def destination_for_source(data_source):
    destination = Path(settings.SYNC_DESTINATION_DIR)
    if data_source.destination_subdir:
        destination = destination / data_source.destination_subdir
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def build_rsync_command(data_source):
    source = data_source.source_path or settings.SYNC_SOURCE_RSYNC
    if not source:
        raise ValueError("SYNC_SOURCE_RSYNC or data source path must be configured.")

    command = ["rsync", "-av", "--ignore-existing", "--itemize-changes"]
    for extension in data_source.extension_list():
        command.extend(["--include", f"*{extension}"])
    command.extend(["--exclude", "*"])
    if settings.SYNC_SSH_KEY:
        command.extend(["-e", f"ssh -i {settings.SYNC_SSH_KEY} -o BatchMode=yes"])
    command.extend([source, str(destination_for_source(data_source)) + "/"])
    return command


def scan_destination(data_source, sync_job, uploaded_names):
    destination = destination_for_source(data_source)
    allowed = set(data_source.extension_list())
    found = existing = uploaded = 0
    for path in sorted(destination.iterdir()):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        found += 1
        checksum = file_checksum(path)
        stored_file, created = StoredFile.objects.get_or_create(
            server_path=str(path),
            defaults={
                "data_source": data_source,
                "submodule": data_source.submodule,
                "original_name": path.name,
                "checksum": checksum,
                "size": path.stat().st_size,
                "modified_time": timezone.datetime.fromtimestamp(
                    path.stat().st_mtime,
                    tz=timezone.get_current_timezone(),
                ),
            },
        )
        action = SyncJobFile.ACTION_UPLOADED if path.name in uploaded_names or created else SyncJobFile.ACTION_EXISTING
        if action == SyncJobFile.ACTION_UPLOADED:
            uploaded += 1
        else:
            existing += 1
        SyncJobFile.objects.create(sync_job=sync_job, stored_file=stored_file, file_name=path.name, action=action)
    return found, existing, uploaded


def parse_uploaded_names(stdout):
    uploaded = set()
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.endswith("/") or line.startswith("sending ") or line.startswith("sent "):
            continue
        if line.startswith(">f") or line.startswith("cd"):
            uploaded.add(line.split()[-1])
    return uploaded


def synchronize_data_source(data_source, user=None):
    sync_job = SyncJob.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        data_source=data_source,
    )
    try:
        command = build_rsync_command(data_source)
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=settings.SYNC_TIMEOUT_SECONDS,
        )
        uploaded_names = parse_uploaded_names(result.stdout)
        found, existing, uploaded = scan_destination(data_source, sync_job, uploaded_names)
        sync_job.stdout = result.stdout
        sync_job.stderr = result.stderr
        sync_job.files_found = found
        sync_job.files_existing = existing
        sync_job.files_uploaded = uploaded
        if result.returncode != 0:
            sync_job.status = SyncJob.STATUS_ERROR
            sync_job.error_message = result.stderr or f"rsync exited with code {result.returncode}"
        sync_job.finished_at = timezone.now()
        sync_job.save()
        log_action(
            user=user,
            action_type="folder_sync",
            status=AuditLog.STATUS_ERROR if sync_job.status == SyncJob.STATUS_ERROR else AuditLog.STATUS_SUCCESS,
            module=data_source.submodule.module,
            submodule=data_source.submodule,
            related_object=str(data_source),
            error_message=sync_job.error_message,
            metadata={
                "files_found": found,
                "files_existing": existing,
                "files_uploaded": uploaded,
            },
        )
    except Exception as exc:
        sync_job.status = SyncJob.STATUS_ERROR
        sync_job.error_message = str(exc)
        sync_job.finished_at = timezone.now()
        sync_job.save()
        SyncJobFile.objects.create(sync_job=sync_job, file_name="", action=SyncJobFile.ACTION_ERROR, message=str(exc))
        log_action(
            user=user,
            action_type="folder_sync",
            status=AuditLog.STATUS_ERROR,
            module=data_source.submodule.module,
            submodule=data_source.submodule,
            related_object=str(data_source),
            error_message=str(exc),
        )
    return sync_job
