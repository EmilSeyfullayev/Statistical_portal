from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from apps.filesync.models import SyncJob
from apps.filesync.services import synchronize_data_source
from .models import DashboardDefinition, DataSource, Module, ModulePermission, Submodule


class SubmoduleInline(admin.TabularInline):
    model = Submodule
    extra = 0


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubmoduleInline]
    search_fields = ("name",)


@admin.register(Submodule)
class SubmoduleAdmin(admin.ModelAdmin):
    list_display = ("name", "module", "order", "is_active")
    list_filter = ("module", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "module__name")


@admin.register(DashboardDefinition)
class DashboardDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    filter_horizontal = ("modules", "submodules")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = ("module", "submodule", "user", "group", "can_view", "can_import", "can_manage")
    list_filter = ("module", "can_view", "can_import", "can_manage")


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "submodule", "source_type", "parser_key", "is_active", "sync_button")
    list_filter = ("source_type", "is_active", "submodule__module")
    search_fields = ("name", "source_path", "parser_key")
    actions = ("synchronize_selected_sources",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:source_id>/sync/",
                self.admin_site.admin_view(self.sync_data_source),
                name="catalog_datasource_sync",
            )
        ]
        return custom_urls + urls

    def sync_button(self, obj):
        url = reverse("admin:catalog_datasource_sync", args=[obj.id])
        return format_html('<a class="button" href="{}">Synchronize</a>', url)

    sync_button.short_description = "Folder sync"

    def sync_data_source(self, request, source_id):
        data_source = DataSource.objects.select_related("submodule__module").get(id=source_id)
        sync_job = synchronize_data_source(data_source, request.user)
        if sync_job.status == SyncJob.STATUS_SUCCESS:
            self.message_user(
                request,
                f"Sync completed for {data_source.name}: {sync_job.files_uploaded} uploaded, "
                f"{sync_job.files_existing} existing.",
                messages.SUCCESS,
            )
        else:
            self.message_user(request, f"Sync failed for {data_source.name}: {sync_job.error_message}", messages.ERROR)
        return redirect("admin:catalog_datasource_changelist")

    @admin.action(description="Synchronize selected folders from desktop/server source")
    def synchronize_selected_sources(self, request, queryset):
        success_count = 0
        error_count = 0
        for data_source in queryset.select_related("submodule__module"):
            sync_job = synchronize_data_source(data_source, request.user)
            if sync_job.status == SyncJob.STATUS_SUCCESS:
                success_count += 1
            else:
                error_count += 1
        if success_count:
            self.message_user(request, f"{success_count} data source(s) synchronized.", messages.SUCCESS)
        if error_count:
            self.message_user(request, f"{error_count} data source sync job(s) failed.", messages.ERROR)

# Register your models here.
