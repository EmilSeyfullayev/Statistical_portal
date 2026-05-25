from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action_type", "status", "module", "submodule", "file_or_report")
    list_filter = ("status", "action_type", "module", "submodule")
    search_fields = ("user__username", "related_object", "file_or_report", "error_message")
    readonly_fields = ("metadata",)

# Register your models here.
