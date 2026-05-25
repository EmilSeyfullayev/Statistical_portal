from django.conf import settings
from django.db import models


class ImportJob(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_ERROR, "Error"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    stored_file = models.ForeignKey("filesync.StoredFile", on_delete=models.SET_NULL, blank=True, null=True)
    submodule = models.ForeignKey("catalog.Submodule", on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    rows_imported = models.PositiveIntegerField(default=0)
    duplicate_decision = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        file_name = self.stored_file.original_name if self.stored_file else "Unknown file"
        return f"{file_name} ({self.status})"


class ProcessedArtifact(models.Model):
    import_job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="artifacts")
    processor_key = models.CharField(max_length=100)
    file_path = models.CharField(max_length=700, blank=True)
    status = models.CharField(max_length=20, default=ImportJob.STATUS_SUCCESS)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.processor_key} - {self.status}"


class TransitRecord(models.Model):
    source_file = models.ForeignKey("filesync.StoredFile", on_delete=models.CASCADE, related_name="transit_records")
    import_job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="transit_records")
    row_number = models.PositiveIntegerField()
    date = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=255, blank=True)
    corridor = models.CharField(max_length=255, blank=True)
    post = models.CharField(max_length=255, blank=True)
    cargo_name = models.CharField(max_length=255, blank=True)
    weight_tons = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["source_file", "row_number"]
        unique_together = [("source_file", "row_number")]

    def __str__(self):
        return f"{self.source_file} row {self.row_number}"

# Create your models here.
