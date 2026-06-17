from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("statistics/", views.statistics, name="statistics"),
    path("track-report-language/", views.track_report_language, name="track_report_language"),
]
