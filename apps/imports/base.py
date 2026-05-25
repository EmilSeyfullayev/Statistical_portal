from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.filesync.models import StoredFile
from apps.imports.models import ImportJob


class BaseImporter:
    parser_key = ""

    def __init__(self, stored_file, user=None, replace=False):
        self.stored_file = stored_file
        self.user = user
        self.replace = replace

    def should_skip_duplicate(self):
        return self.stored_file.import_status == StoredFile.STATUS_IMPORTED and not self.replace

    def run(self):
        if self.should_skip_duplicate():
            return ImportJob.objects.create(
                user=self.user,
                stored_file=self.stored_file,
                submodule=self.stored_file.submodule,
                status=ImportJob.STATUS_SKIPPED,
                duplicate_decision="prevented",
                error_message="File was already imported.",
                finished_at=timezone.now(),
            )
        job = ImportJob.objects.create(
            user=self.user if getattr(self.user, "is_authenticated", False) else None,
            stored_file=self.stored_file,
            submodule=self.stored_file.submodule,
        )
        try:
            rows_imported = self.import_rows(job)
            job.rows_imported = rows_imported
            job.status = ImportJob.STATUS_SUCCESS
            job.finished_at = timezone.now()
            job.save()
            self.stored_file.import_status = StoredFile.STATUS_IMPORTED
            self.stored_file.save(update_fields=["import_status", "updated_at"])
            log_action(
                user=self.user,
                action_type="database_import",
                status=AuditLog.STATUS_SUCCESS,
                module=self.stored_file.submodule.module if self.stored_file.submodule else None,
                submodule=self.stored_file.submodule,
                file_or_report=self.stored_file.original_name,
                metadata={"rows_imported": rows_imported},
            )
        except Exception as exc:
            job.status = ImportJob.STATUS_ERROR
            job.error_message = str(exc)
            job.finished_at = timezone.now()
            job.save()
            self.stored_file.import_status = StoredFile.STATUS_ERROR
            self.stored_file.save(update_fields=["import_status", "updated_at"])
            log_action(
                user=self.user,
                action_type="database_import",
                status=AuditLog.STATUS_ERROR,
                module=self.stored_file.submodule.module if self.stored_file.submodule else None,
                submodule=self.stored_file.submodule,
                file_or_report=self.stored_file.original_name,
                error_message=str(exc),
            )
        return job

    def import_rows(self, job):
        raise NotImplementedError
