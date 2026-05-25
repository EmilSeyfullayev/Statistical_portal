from django.conf import settings
from django.db import models


class InteractionEvent(models.Model):
    DASHBOARD_VIEW = "dashboard_view"
    MODULE_VIEW = "module_view"
    SUBMODULE_VIEW = "submodule_view"
    REPORT_LINK_CLICK = "report_link_click"
    REPORT_PREVIEW = "report_preview"
    REPORT_DOWNLOAD_START = "report_download_start"
    EVENT_TYPE_CHOICES = [
        (DASHBOARD_VIEW, "Dashboard view"),
        (MODULE_VIEW, "Module view"),
        (SUBMODULE_VIEW, "Submodule view"),
        (REPORT_LINK_CLICK, "Report link click"),
        (REPORT_PREVIEW, "Report preview"),
        (REPORT_DOWNLOAD_START, "Report download start"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    module = models.ForeignKey("catalog.Module", on_delete=models.SET_NULL, blank=True, null=True)
    submodule = models.ForeignKey("catalog.Submodule", on_delete=models.SET_NULL, blank=True, null=True)
    dashboard = models.ForeignKey("catalog.DashboardDefinition", on_delete=models.SET_NULL, blank=True, null=True)
    report = models.ForeignKey("reports.ReportDefinition", on_delete=models.SET_NULL, blank=True, null=True)
    target_url = models.CharField(max_length=700, blank=True)
    request_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} at {self.created_at:%Y-%m-%d %H:%M}"


class InteractionDailyStat(models.Model):
    date = models.DateField()
    event_type = models.CharField(max_length=50, choices=InteractionEvent.EVENT_TYPE_CHOICES)
    module = models.ForeignKey("catalog.Module", on_delete=models.CASCADE, blank=True, null=True)
    submodule = models.ForeignKey("catalog.Submodule", on_delete=models.CASCADE, blank=True, null=True)
    dashboard = models.ForeignKey("catalog.DashboardDefinition", on_delete=models.CASCADE, blank=True, null=True)
    report = models.ForeignKey("reports.ReportDefinition", on_delete=models.CASCADE, blank=True, null=True)
    total_count = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("date", "event_type", "module", "submodule", "dashboard", "report")]
        ordering = ["-date", "event_type"]

    def __str__(self):
        return f"{self.date} {self.event_type}: {self.total_count}"

# Create your models here.
