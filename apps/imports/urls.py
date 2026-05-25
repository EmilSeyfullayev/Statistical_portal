from django.urls import path

from . import views

app_name = "imports"

urlpatterns = [
    path("files/<int:file_id>/", views.import_file, name="import_file"),
    path("jobs/<int:job_id>/", views.import_detail, name="import_detail"),
]
