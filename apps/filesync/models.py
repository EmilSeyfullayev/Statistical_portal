from django.conf import settings
from django.db import models


class StoredFile(models.Model):
    STATUS_PENDING = "pending"
    STATUS_IMPORTED = "imported"
    STATUS_ERROR = "error"
    IMPORT_STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IMPORTED, "Imported"),
        (STATUS_ERROR, "Error"),
    ]

    data_source = models.ForeignKey("catalog.DataSource", on_delete=models.SET_NULL, blank=True, null=True)
    submodule = models.ForeignKey("catalog.Submodule", on_delete=models.SET_NULL, blank=True, null=True)
    original_name = models.CharField(max_length=255)
    server_path = models.CharField(max_length=700, unique=True)
    checksum = models.CharField(max_length=64, db_index=True)
    size = models.BigIntegerField(default=0)
    modified_time = models.DateTimeField(blank=True, null=True)
    import_status = models.CharField(max_length=20, choices=IMPORT_STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name


class SyncJob(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [(STATUS_SUCCESS, "Success"), (STATUS_ERROR, "Error")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    data_source = models.ForeignKey("catalog.DataSource", on_delete=models.SET_NULL, blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    files_found = models.PositiveIntegerField(default=0)
    files_existing = models.PositiveIntegerField(default=0)
    files_uploaded = models.PositiveIntegerField(default=0)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Sync {self.started_at:%Y-%m-%d %H:%M} ({self.status})"


class SyncJobFile(models.Model):
    ACTION_UPLOADED = "uploaded"
    ACTION_EXISTING = "existing"
    ACTION_SKIPPED = "skipped"
    ACTION_ERROR = "error"
    ACTION_CHOICES = [
        (ACTION_UPLOADED, "Uploaded"),
        (ACTION_EXISTING, "Existing"),
        (ACTION_SKIPPED, "Skipped"),
        (ACTION_ERROR, "Error"),
    ]

    sync_job = models.ForeignKey(SyncJob, on_delete=models.CASCADE, related_name="files")
    stored_file = models.ForeignKey(StoredFile, on_delete=models.SET_NULL, blank=True, null=True)
    file_name = models.CharField(max_length=255)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["file_name"]

    def __str__(self):
        return f"{self.file_name} - {self.action}"

# Create your models here.
