from django.contrib import admin

from .models import ReportDefinition, ReportDownload


@admin.register(ReportDefinition)
class ReportDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "submodule", "format", "generator_key", "is_active")
    list_filter = ("format", "is_active", "submodule__module")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "generator_key")


@admin.register(ReportDownload)
class ReportDownloadAdmin(admin.ModelAdmin):
    list_display = ("downloaded_at", "user", "report", "module", "submodule", "format")
    list_filter = ("format", "module", "submodule")
    search_fields = ("report__name", "user__username")

# Register your models here.
