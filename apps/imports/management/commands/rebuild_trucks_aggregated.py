from django.core.management.base import BaseCommand

from apps.imports.services.trucks_aggregated import rebuild_trucks_aggregated


class Command(BaseCommand):
    help = "Build trucks.trucks_aggregated directly from local and foreign merged truck tables."

    def handle(self, *args, **options):
        result = rebuild_trucks_aggregated()
        self.stdout.write(
            self.style.SUCCESS(
                f"Built {result.aggregated_table} with {result.aggregated_row_count} rows."
            )
        )
