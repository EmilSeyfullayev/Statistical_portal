from django.contrib import admin

from apps.accounts.services import get_user_display_name

from .models import InteractionDailyStat, InteractionEvent


@admin.register(InteractionEvent)
class InteractionEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user_display",
        "event_type",
        "module",
        "submodule",
        "dashboard",
        "report_display",
        "format_display",
        "target_url",
    )
    list_filter = ("event_type", "module", "submodule", "dashboard")
    search_fields = ("user__username", "target_url", "report__name")

    def user_display(self, obj):
        if not obj.user:
            return "-"
        display_name = get_user_display_name(obj.user)
        return f"{display_name} ({obj.user.username})" if display_name != obj.user.username else obj.user.username

    user_display.short_description = "User"

    def report_display(self, obj):
        if obj.report:
            return obj.report.name
        return obj.request_metadata.get("report_name", "-")

    report_display.short_description = "Report"

    def format_display(self, obj):
        return obj.request_metadata.get("format", "-")

    format_display.short_description = "Format"


@admin.register(InteractionDailyStat)
class InteractionDailyStatAdmin(admin.ModelAdmin):
    list_display = ("date", "event_type", "module", "submodule", "dashboard", "report", "total_count", "unique_users")
    list_filter = ("date", "event_type")

# Register your models here.
