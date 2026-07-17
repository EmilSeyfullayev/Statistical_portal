from django.core.management.base import BaseCommand

from apps.imports.services.trucks_enter_exit_preview import (
    DEFAULT_OUTPUT_PATH,
    export_trucks_enter_exit_preview,
)


class Command(BaseCommand):
    help = "Export a temporary Excel preview of truck enter/exit one-line data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(DEFAULT_OUTPUT_PATH),
            help=f"Excel output path. Defaults to {DEFAULT_OUTPUT_PATH}.",
        )

    def handle(self, *args, **options):
        result = export_trucks_enter_exit_preview(options["output"])
        self.stdout.write(self.style.SUCCESS(f"Exported {result.output_path}"))
        self.stdout.write(f"Total rows: {result.row_count}")
        self.stdout.write(f"Rows by Rejim: {result.regime_counts}")
        self.stdout.write(f"Date coverage: {result.min_datesign} to {result.max_datesign}")
        self.stdout.write(
            "Side coverage: "
            f"entrance_only={result.entrance_only_count}, "
            f"exit_only={result.exit_only_count}, "
            f"both_sides={result.both_sides_count}"
        )
