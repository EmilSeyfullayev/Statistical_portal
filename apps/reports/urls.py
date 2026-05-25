from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("<int:report_id>/download/", views.download, name="download"),
]
