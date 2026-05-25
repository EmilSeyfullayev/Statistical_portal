from django.contrib import admin

from .models import ImportJob, ProcessedArtifact, TransitRecord


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("started_at", "stored_file", "submodule", "status", "rows_imported")
    list_filter = ("status", "submodule__module", "submodule")
    search_fields = ("stored_file__original_name", "error_message")


@admin.register(ProcessedArtifact)
class ProcessedArtifactAdmin(admin.ModelAdmin):
    list_display = ("import_job", "processor_key", "status", "created_at")
    list_filter = ("status", "processor_key")


@admin.register(TransitRecord)
class TransitRecordAdmin(admin.ModelAdmin):
    list_display = ("source_file", "row_number", "date", "country", "corridor", "weight_tons")
    list_filter = ("country", "corridor")
    search_fields = ("country", "corridor", "post", "cargo_name")

# Register your models here.
