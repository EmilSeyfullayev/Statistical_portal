from django.contrib import admin

from .models import StoredFile, SyncJob, SyncJobFile


class SyncJobFileInline(admin.TabularInline):
    model = SyncJobFile
    extra = 0
    readonly_fields = ("stored_file", "file_name", "action", "message")


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "submodule", "import_status", "size", "created_at")
    list_filter = ("import_status", "submodule__module", "submodule")
    search_fields = ("original_name", "server_path", "checksum")


@admin.register(SyncJob)
class SyncJobAdmin(admin.ModelAdmin):
    list_display = ("started_at", "user", "status", "files_found", "files_existing", "files_uploaded")
    list_filter = ("status", "data_source")
    readonly_fields = ("stdout", "stderr", "error_message")
    inlines = [SyncJobFileInline]


@admin.register(SyncJobFile)
class SyncJobFileAdmin(admin.ModelAdmin):
    list_display = ("file_name", "sync_job", "action")
    list_filter = ("action",)

# Register your models here.
