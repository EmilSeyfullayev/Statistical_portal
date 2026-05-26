from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.accounts.services import ADMIN_GROUP, MODULE_RESPONSIBLE_GROUP, WORKER_GROUP
from apps.catalog.models import DashboardDefinition, DataSource, Module, Submodule
from apps.reports.models import ReportDefinition


MODULES = [
    (
        "Tranzit daşımalar",
        "",
        [
            "Dinamika arayışı",
            "Ölkələr üzrə arayış",
            "Dəhlizlər üzrə arayış",
            "Postlar üzrə arayış",
            "Blok qatarlar",
            "Gəlirlər",
            "Qonşu ölkələrlə yük dövriyyəsi, rejimlər üzrə",
        ],
    ),
    ("Ölkələrin profili üzrə hesabatlar", "", ["İdxal/İxrac/Tranzit"]),
    ("Sahələr üzrə arayışlar", "", ["ADY", "PoB", "TIR-lar", "AZAL"]),
    ("Təşkilatlar üzrə arayışlar", "", ["ECO", "Türkdilli dövlətlər", "TRACECA"]),
    (
        "Raw data",
        "datalar",
        [
            "Tranzit",
            "Xarici TIR-lar",
            "Yerli TIR-lar",
            "ADY / Azerbaijan Railways",
            "İdxal / İxrac",
            "PortOfBaku",
            "AZAL / Azerbaijan Airlines",
        ],
    ),
    ("Processed Data", "processed-data", ["Transit"]),
]

DASHBOARDS = ["Transit", "İdxal/İxrac/Tranzit", "ADY", "PoB"]


def make_slug(value):
    return slugify(value, allow_unicode=True).replace("/", "-")


class Command(BaseCommand):
    help = "Seed ministry portal roles, modules, dashboards, data sources, and first report."

    def handle(self, *args, **options):
        self.create_groups()
        submodules_by_name = {}
        for module_order, (module_name, module_slug, submodule_names) in enumerate(MODULES, start=1):
            module, _ = Module.objects.update_or_create(
                slug=module_slug or make_slug(module_name),
                defaults={"name": module_name, "order": module_order, "is_active": True},
            )
            for submodule_order, submodule_name in enumerate(submodule_names, start=1):
                submodule, _ = Submodule.objects.update_or_create(
                    module=module,
                    slug=make_slug(submodule_name),
                    defaults={"name": submodule_name, "order": submodule_order, "is_active": True},
                )
                submodules_by_name[submodule_name] = submodule

        for order, dashboard_name in enumerate(DASHBOARDS, start=1):
            DashboardDefinition.objects.update_or_create(
                slug=make_slug(dashboard_name),
                defaults={"name": dashboard_name, "order": order, "is_active": True},
            )

        transit_submodule = submodules_by_name["Tranzit"]
        DataSource.objects.update_or_create(
            submodule=transit_submodule,
            name="Transit Excel source",
            defaults={
                "source_type": DataSource.SOURCE_RSYNC,
                "destination_subdir": "transit",
                "parser_key": "transit_excel_v1",
                "target_model_key": "transit_record",
                "duplicate_strategy": "prevent",
                "is_active": True,
            },
        )
        ReportDefinition.objects.update_or_create(
            submodule=transit_submodule,
            slug="transit-word-report",
            defaults={
                "name": "Transit Microsoft Word report",
                "format": ReportDefinition.FORMAT_DOCX,
                "generator_key": "transit_docx_v1",
                "is_active": True,
                "order": 1,
            },
        )
        ReportDefinition.objects.update_or_create(
            submodule=transit_submodule,
            slug="transit-pdf-report",
            defaults={
                "name": "Transit PDF report",
                "format": ReportDefinition.FORMAT_PDF,
                "generator_key": "transit_pdf_v1",
                "is_active": True,
                "order": 2,
            },
        )
        self.stdout.write(self.style.SUCCESS("Portal catalog seeded."))

    def create_groups(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        Group.objects.get_or_create(name=MODULE_RESPONSIBLE_GROUP)
        Group.objects.get_or_create(name=WORKER_GROUP)
        admin_group.permissions.set(Permission.objects.all())
