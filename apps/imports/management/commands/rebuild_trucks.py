from django.core.management.base import BaseCommand

from apps.imports.services.trucks import rebuild_trucks


class Command(BaseCommand):
    help = "Build trucks.trucks and trucks.trucks_aggregated from local and foreign merged truck tables."

    def handle(self, *args, **options):
        result = rebuild_trucks()
        self.stdout.write(
            self.style.SUCCESS(
                f"Built {result.trucks_table} with {result.trucks_row_count} rows and "
                f"{result.aggregated_table} with {result.aggregated_row_count} rows."
            )
        )
