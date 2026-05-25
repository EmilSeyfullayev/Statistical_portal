from django.contrib.auth.models import Group, User
from django.db import models
from django.urls import reverse


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Module(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dashboard:module_detail", kwargs={"module_slug": self.slug})


class Submodule(TimeStampedModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="submodules")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, allow_unicode=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["module__order", "order", "name"]
        unique_together = [("module", "slug")]

    def __str__(self):
        return f"{self.module} / {self.name}"

    def get_absolute_url(self):
        return reverse(
            "dashboard:submodule_detail",
            kwargs={"module_slug": self.module.slug, "submodule_slug": self.slug},
        )


class DashboardDefinition(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    modules = models.ManyToManyField(Module, blank=True, related_name="dashboards")
    submodules = models.ManyToManyField(Submodule, blank=True, related_name="dashboards")

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ModulePermission(TimeStampedModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="permissions")
    submodule = models.ForeignKey(
        Submodule,
        on_delete=models.CASCADE,
        related_name="permissions",
        blank=True,
        null=True,
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, blank=True, null=True)
    can_view = models.BooleanField(default=True)
    can_import = models.BooleanField(default=False)
    can_manage = models.BooleanField(default=False)

    class Meta:
        ordering = ["module__name", "submodule__name"]

    def __str__(self):
        target = self.user or self.group
        return f"{target} -> {self.submodule or self.module}"


class DataSource(TimeStampedModel):
    SOURCE_RSYNC = "rsync"
    SOURCE_LOCAL = "local"
    SOURCE_CHOICES = [(SOURCE_RSYNC, "Rsync"), (SOURCE_LOCAL, "Local folder")]

    submodule = models.ForeignKey(Submodule, on_delete=models.CASCADE, related_name="data_sources")
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_RSYNC)
    source_path = models.CharField(max_length=500, blank=True)
    destination_subdir = models.CharField(max_length=255, blank=True)
    accepted_extensions = models.CharField(max_length=255, default=".xlsx,.xls,.xlsm,.csv")
    parser_key = models.CharField(max_length=100, blank=True)
    processor_key = models.CharField(max_length=100, blank=True)
    target_model_key = models.CharField(max_length=100, blank=True)
    duplicate_strategy = models.CharField(max_length=50, default="prevent")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["submodule__module__order", "submodule__order", "name"]

    def __str__(self):
        return f"{self.submodule} - {self.name}"

    def extension_list(self):
        return [item.strip().lower() for item in self.accepted_extensions.split(",") if item.strip()]

# Create your models here.
