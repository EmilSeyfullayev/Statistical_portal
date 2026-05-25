from django.urls import path

from . import views

app_name = "filesync"

urlpatterns = [
    path("sync/<int:source_id>/", views.sync_source, name="sync_source"),
    path("sync-jobs/<int:job_id>/", views.sync_detail, name="sync_detail"),
]
