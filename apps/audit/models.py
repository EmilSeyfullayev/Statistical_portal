from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_INFO = "info"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_ERROR, "Error"),
        (STATUS_INFO, "Info"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    action_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_INFO)
    module = models.ForeignKey("catalog.Module", on_delete=models.SET_NULL, blank=True, null=True)
    submodule = models.ForeignKey("catalog.Submodule", on_delete=models.SET_NULL, blank=True, null=True)
    related_object = models.CharField(max_length=255, blank=True)
    file_or_report = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action_type} {self.status}"

# Create your models here.
