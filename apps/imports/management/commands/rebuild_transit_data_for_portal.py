from django.core.management.base import BaseCommand

from apps.imports.services.transit_portal import (
    rebuild_transit_dashboard_table,
    rebuild_transit_data_for_portal,
)


class Command(BaseCommand):
    help = "Rebuild transit.transit_data_for_portal from transit.transit_merged."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dayfirst",
            action="store_true",
            help="Parse source date strings as day-first values.",
        )

    def handle(self, *args, **options):
        result = rebuild_transit_data_for_portal(dayfirst=options["dayfirst"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Rebuilt {result.portal_table} from {result.source_table} "
                f"with {result.portal_row_count} rows "
                f"({result.source_row_count} source rows)."
            )
        )
        dashboard_result = rebuild_transit_dashboard_table()
        self.stdout.write(
            self.style.SUCCESS(
                f"Rebuilt {dashboard_result.dashboard_table} from {dashboard_result.source_table} "
                f"with {dashboard_result.dashboard_row_count} rows "
                f"({dashboard_result.source_row_count} source rows)."
            )
        )
