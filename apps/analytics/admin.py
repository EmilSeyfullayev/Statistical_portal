from django.contrib import admin

from .models import InteractionDailyStat, InteractionEvent


@admin.register(InteractionEvent)
class InteractionEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "event_type", "module", "submodule", "dashboard", "report")
    list_filter = ("event_type", "module", "submodule", "dashboard")
    search_fields = ("user__username", "target_url", "report__name")


@admin.register(InteractionDailyStat)
class InteractionDailyStatAdmin(admin.ModelAdmin):
    list_display = ("date", "event_type", "module", "submodule", "dashboard", "report", "total_count", "unique_users")
    list_filter = ("date", "event_type")

# Register your models here.
