from django.conf import settings
from django.db import models


class ReportDefinition(models.Model):
    FORMAT_DOCX = "docx"
    FORMAT_PDF = "pdf"
    FORMAT_CHOICES = [(FORMAT_DOCX, "Microsoft Word"), (FORMAT_PDF, "PDF")]

    submodule = models.ForeignKey("catalog.Submodule", on_delete=models.CASCADE, related_name="reports")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, allow_unicode=True)
    description = models.TextField(blank=True)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default=FORMAT_DOCX)
    generator_key = models.CharField(max_length=100)
    template_path = models.CharField(max_length=700, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["submodule__module__order", "submodule__order", "order", "name"]
        unique_together = [("submodule", "slug")]

    def __str__(self):
        return f"{self.submodule} - {self.name}"


class ReportDownload(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    report = models.ForeignKey(ReportDefinition, on_delete=models.SET_NULL, blank=True, null=True)
    module = models.ForeignKey("catalog.Module", on_delete=models.SET_NULL, blank=True, null=True)
    submodule = models.ForeignKey("catalog.Submodule", on_delete=models.SET_NULL, blank=True, null=True)
    format = models.CharField(max_length=20, default=ReportDefinition.FORMAT_DOCX)
    generated_file_path = models.CharField(max_length=700, blank=True)
    request_metadata = models.JSONField(default=dict, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-downloaded_at"]

    def __str__(self):
        report_name = self.report.name if self.report else "Unknown report"
        return f"{report_name} by {self.user}"

# Create your models here.
