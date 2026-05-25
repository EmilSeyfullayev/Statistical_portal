from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboards/<str:dashboard_slug>/", views.dashboard_detail, name="dashboard_detail"),
    path("modules/<str:module_slug>/", views.module_detail, name="module_detail"),
    path(
        "modules/<str:module_slug>/<str:submodule_slug>/",
        views.submodule_detail,
        name="submodule_detail",
    ),
]
