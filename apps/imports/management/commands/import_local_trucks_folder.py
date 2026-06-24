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
from apps.imports.services.local_trucks_merge import rebuild_local_trucks_merged


class Command(BaseCommand):
    help = "Register and import every Local Trucks Excel workbook into local_trucks tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Re-import files even when they were already imported.",
        )
        parser.add_argument(
            "--path",
            default="",
            help="Override the Local Trucks upload folder. Defaults to the seeded data source destination.",
        )
        parser.add_argument(
            "--skip-merge",
            action="store_true",
            help="Do not rebuild local_trucks.local_trucks_merged after importing files.",
        )

    def handle(self, *args, **options):
        data_source = self.get_local_trucks_data_source()
        source_dir = self.source_directory(data_source, options["path"])
        if not source_dir.exists():
            raise CommandError(f"Local Trucks folder does not exist: {source_dir}")

        importer_class = get_importer(data_source.parser_key)
        files = self.local_trucks_files(source_dir)
        if not files:
            self.stdout.write(self.style.WARNING(f"No Local Trucks Excel files found in {source_dir}"))
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
                self.stdout.write(
                    f"Imported {path.relative_to(source_dir)} -> local_trucks.{table_name} "
                    f"({job.rows_imported} rows)"
                )
            elif job.status == ImportJob.STATUS_SKIPPED:
                totals["skipped"] += 1
                self.stdout.write(f"Skipped {path.relative_to(source_dir)}: {job.error_message}")
            else:
                totals["errors"] += 1
                self.stderr.write(f"Failed {path.relative_to(source_dir)}: {job.error_message}")

        summary = (
            f"Local Trucks import complete: {totals['imported']} imported, "
            f"{totals['skipped']} skipped, {totals['errors']} errors, {totals['rows']} rows."
        )
        if totals["errors"]:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
        if not options["skip_merge"]:
            result = rebuild_local_trucks_merged()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Rebuilt {result.merged_table} from {result.source_table_count} source tables "
                    f"with {result.merged_row_count} rows."
                )
            )

    def get_local_trucks_data_source(self):
        SeedCommand().handle()
        data_source = DataSource.objects.filter(
            parser_key="local_trucks_excel_v1",
            submodule__name="Yerli TIR-lar",
        ).select_related("submodule__module").first()
        if not data_source:
            raise CommandError("Local Trucks data source was not found after seeding.")
        return data_source

    def source_directory(self, data_source, override_path):
        if override_path:
            return Path(override_path).expanduser().resolve()
        source_dir = Path(settings.SYNC_DESTINATION_DIR)
        if data_source.destination_subdir:
            source_dir = source_dir / data_source.destination_subdir
        return source_dir.resolve()

    def local_trucks_files(self, source_dir):
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
