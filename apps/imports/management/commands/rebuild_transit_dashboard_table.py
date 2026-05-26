from django.core.management.base import BaseCommand

from apps.imports.services.transit_portal import rebuild_transit_dashboard_table


class Command(BaseCommand):
    help = "Rebuild transit.transit_for_dashboard_on_ministry_portal from transit.transit_data_for_portal."

    def handle(self, *args, **options):
        result = rebuild_transit_dashboard_table()
        self.stdout.write(
            self.style.SUCCESS(
                f"Rebuilt {result.dashboard_table} from {result.source_table} "
                f"with {result.dashboard_row_count} rows "
                f"({result.source_row_count} source rows)."
            )
        )
