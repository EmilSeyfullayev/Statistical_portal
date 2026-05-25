from django.core.management.base import BaseCommand

from apps.imports.services.transit_merge import OMITTED_SOURCE_TABLES, rebuild_transit_merged
from apps.imports.services.transit_portal import rebuild_transit_data_for_portal


class Command(BaseCommand):
    help = "Rebuild the merged Transit table from per-file tables in the transit schema."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-portal-table",
            action="store_true",
            help="Also rebuild transit.transit_data_for_portal from transit.transit_merged.",
        )

    def handle(self, *args, **options):
        for table_name, reason in OMITTED_SOURCE_TABLES.items():
            self.stdout.write(f"Skipping {table_name}: {reason}")
        result = rebuild_transit_merged()
        self.stdout.write(
            self.style.SUCCESS(
                f"Rebuilt {result.merged_table} from {result.source_table_count} source tables "
                f"with {result.merged_row_count} rows."
            )
        )
        if options["with_portal_table"]:
            portal_result = rebuild_transit_data_for_portal()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Rebuilt {portal_result.portal_table} from {portal_result.source_table} "
                    f"with {portal_result.portal_row_count} rows "
                    f"({portal_result.source_row_count} source rows)."
                )
            )
