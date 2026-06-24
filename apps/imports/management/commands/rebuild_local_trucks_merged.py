from django.core.management.base import BaseCommand

from apps.imports.services.local_trucks_merge import rebuild_local_trucks_merged


class Command(BaseCommand):
    help = "Rebuild local_trucks.local_trucks_merged from per-file Local Trucks tables."

    def handle(self, *args, **options):
        result = rebuild_local_trucks_merged()
        self.stdout.write(
            self.style.SUCCESS(
                f"Rebuilt {result.merged_table} from {result.source_table_count} source tables "
                f"with {result.merged_row_count} rows."
            )
        )
