from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.catalog.management.commands.seed_portal import Command as SeedCommand
from apps.catalog.models import DataSource
from apps.filesync.models import StoredFile
from apps.filesync.services import file_checksum
from apps.imports.models import ImportJob
from apps.imports.registry import get_importer
from apps.imports.services.transit_merge import rebuild_transit_merged
from apps.imports.services.transit_portal import rebuild_transit_data_for_portal


class Command(BaseCommand):
    help = "Register and import every Transit Excel workbook into one table per file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Re-import files even when they were already imported.",
        )
        parser.add_argument(
            "--path",
            default="",
            help="Override the Transit upload folder. Defaults to the seeded Transit data source destination.",
        )
        parser.add_argument(
            "--skip-merge",
            action="store_true",
            help="Do not rebuild transit.transit_merged after importing files.",
        )
        parser.add_argument(
            "--skip-portal-table",
            action="store_true",
            help="Do not rebuild transit.transit_data_for_portal after rebuilding transit.transit_merged.",
        )

    def handle(self, *args, **options):
        data_source = self.get_transit_data_source()
        source_dir = self.source_directory(data_source, options["path"])
        if not source_dir.exists():
            raise CommandError(f"Transit folder does not exist: {source_dir}")

        importer_class = get_importer(data_source.parser_key)
        files = self.transit_files(source_dir)
        if not files:
            self.stdout.write(self.style.WARNING(f"No Transit Excel files found in {source_dir}"))
            return

        totals = {"imported": 0, "skipped": 0, "errors": 0, "rows": 0}
        for path in files:
            stored_file = self.register_file(path, data_source)
            replace = options["replace"] or stored_file.import_status != StoredFile.STATUS_IMPORTED
            job = importer_class(stored_file, replace=replace).run()
            if job.status == ImportJob.STATUS_SUCCESS:
                totals["imported"] += 1
                totals["rows"] += job.rows_imported
                table_name = job.metadata.get("generated_table", "")
                self.stdout.write(f"Imported {path.relative_to(source_dir)} -> {table_name} ({job.rows_imported} rows)")
            elif job.status == ImportJob.STATUS_SKIPPED:
                totals["skipped"] += 1
                self.stdout.write(f"Skipped {path.relative_to(source_dir)}: {job.error_message}")
            else:
                totals["errors"] += 1
                self.stderr.write(f"Failed {path.relative_to(source_dir)}: {job.error_message}")

        summary = (
            f"Transit import complete: {totals['imported']} imported, "
            f"{totals['skipped']} skipped, {totals['errors']} errors, {totals['rows']} rows."
        )
        if totals["errors"]:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
        if not options["skip_merge"]:
            result = rebuild_transit_merged()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Rebuilt {result.merged_table} from {result.source_table_count} source tables "
                    f"with {result.merged_row_count} rows."
                )
            )
            if not options["skip_portal_table"]:
                portal_result = rebuild_transit_data_for_portal()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Rebuilt {portal_result.portal_table} from {portal_result.source_table} "
                        f"with {portal_result.portal_row_count} rows "
                        f"({portal_result.source_row_count} source rows)."
                    )
                )

    def get_transit_data_source(self):
        SeedCommand().handle()
        data_source = DataSource.objects.filter(
            parser_key="transit_excel_v1",
            submodule__name="Tranzit",
        ).select_related("submodule__module").first()
        if not data_source:
            raise CommandError("Transit data source was not found after seeding.")
        return data_source

    def source_directory(self, data_source, override_path):
        if override_path:
            return Path(override_path).expanduser().resolve()
        source_dir = Path(settings.SYNC_DESTINATION_DIR)
        if data_source.destination_subdir:
            source_dir = source_dir / data_source.destination_subdir
        return source_dir.resolve()

    def transit_files(self, source_dir):
        extensions = {".xlsx", ".xlsm"}
        return sorted(
            path
            for path in source_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in extensions
        )

    def register_file(self, path, data_source):
        stat = path.stat()
        checksum = file_checksum(path)
        modified_time = timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())
        existing = StoredFile.objects.filter(server_path=str(path)).first()
        defaults = {
            "data_source": data_source,
            "submodule": data_source.submodule,
            "original_name": path.name,
            "checksum": checksum,
            "size": stat.st_size,
            "modified_time": modified_time,
        }
        if existing and existing.checksum != checksum:
            defaults["import_status"] = StoredFile.STATUS_PENDING
        stored_file, _ = StoredFile.objects.update_or_create(
            server_path=str(path),
            defaults=defaults,
        )
        return stored_file
