import csv
import io
import re
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.imports.base import BaseImporter


LOCAL_TRUCKS_SCHEMA = "local_trucks"
TRACE_COLUMNS = {
    "source_file_path",
    "source_sheet_name",
    "source_row_number",
    "import_job_id",
    "imported_at",
}
DATETIME_COLUMNS = ["DATESIGN", "ENTER_DATE"]
FLOAT_COLUMNS = ["WEIGHT"]


def normalize_identifier(value, *, default):
    normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", str(value).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).lstrip("_")
    if not normalized:
        normalized = default
    if normalized[0].isdigit():
        normalized = f"_{normalized}"
    return normalized[:63]


def local_trucks_table_name(path):
    upload_root = Path(settings.SYNC_DESTINATION_DIR).resolve()
    file_path = Path(path).resolve()
    try:
        relative_path = file_path.relative_to(upload_root)
    except ValueError:
        relative_path = Path(file_path.name)
    table_stem = relative_path.with_suffix("").as_posix()
    table_source = table_stem if table_stem.startswith("local_trucks/") else f"local_trucks/{table_stem}"
    return normalize_identifier(table_source, default="local_trucks_file")


def sheet_name_for(path):
    workbook = pd.ExcelFile(path)
    return workbook.sheet_names[0]


def parse_datetime_column(series):
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series, format="%d.%m.%Y %H:%M:%S", errors="coerce")


def normalize_local_trucks_frame(frame):
    normalized = frame.copy()
    for column in DATETIME_COLUMNS:
        if column in normalized.columns:
            normalized[column] = parse_datetime_column(normalized[column])
    for column in FLOAT_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce").astype("float64")
    return normalized


def prepare_frame(frame, stored_file, job, sheet_name):
    original_columns = [str(column) for column in frame.columns]
    prepared = normalize_local_trucks_frame(frame)
    prepared = prepared.where(pd.notnull(prepared), None)
    prepared.insert(0, "source_file_path", stored_file.server_path)
    prepared.insert(1, "source_sheet_name", sheet_name)
    prepared.insert(2, "source_row_number", range(2, len(prepared) + 2))
    prepared.insert(3, "import_job_id", job.id)
    prepared.insert(4, "imported_at", timezone.now())
    return prepared, original_columns


def sql_type_for(column, series):
    if column in DATETIME_COLUMNS or column == "imported_at":
        return "timestamp with time zone"
    if column in FLOAT_COLUMNS:
        return "double precision"
    if column in {"source_row_number", "import_job_id"}:
        return "bigint"
    if pd.api.types.is_integer_dtype(series):
        return "bigint"
    if pd.api.types.is_float_dtype(series):
        return "double precision"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "timestamp with time zone"
    return "text"


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()
    return value


def serialize_copy_value(value):
    return clean_value(value)


def create_table(cursor, table_name, frame):
    quoted_schema = connection.ops.quote_name(LOCAL_TRUCKS_SCHEMA)
    quoted_table = f"{quoted_schema}.{connection.ops.quote_name(table_name)}"
    column_definitions = [
        f"{connection.ops.quote_name(column)} {sql_type_for(column, frame[column])}"
        for column in frame.columns
    ]
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
    cursor.execute(f"DROP TABLE IF EXISTS {quoted_table}")
    cursor.execute(f"CREATE TABLE {quoted_table} ({', '.join(column_definitions)})")


def insert_frame(cursor, table_name, frame):
    if frame.empty:
        return

    quoted_schema = connection.ops.quote_name(LOCAL_TRUCKS_SCHEMA)
    quoted_table = f"{quoted_schema}.{connection.ops.quote_name(table_name)}"
    quoted_columns = ", ".join(connection.ops.quote_name(column) for column in frame.columns)
    if connection.vendor == "postgresql":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        for row in frame.itertuples(index=False, name=None):
            writer.writerow([serialize_copy_value(value) for value in row])
        buffer.seek(0)
        with cursor.copy(f"COPY {quoted_table} ({quoted_columns}) FROM STDIN WITH CSV") as copy:
            copy.write(buffer.read())
        return

    placeholders = ", ".join(["%s"] * len(frame.columns))
    rows = [
        tuple(clean_value(value) for value in row)
        for row in frame.itertuples(index=False, name=None)
    ]
    cursor.executemany(
        f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})",
        rows,
    )


class LocalTrucksExcelImporter(BaseImporter):
    parser_key = "local_trucks_excel_v1"

    def import_rows(self, job):
        table_name = local_trucks_table_name(self.stored_file.server_path)
        sheet_name = sheet_name_for(self.stored_file.server_path)
        frame = pd.read_excel(self.stored_file.server_path, sheet_name=sheet_name)
        prepared_frame, original_columns = prepare_frame(frame, self.stored_file, job, sheet_name)

        with connection.cursor() as cursor:
            create_table(cursor, table_name, prepared_frame)
            insert_frame(cursor, table_name, prepared_frame)

        job.metadata = {
            **job.metadata,
            "generated_table": table_name,
            "generated_schema": LOCAL_TRUCKS_SCHEMA,
            "source_sheet": sheet_name,
            "original_columns": original_columns,
            "datetime_columns": [column for column in DATETIME_COLUMNS if column in prepared_frame.columns],
            "float_columns": [column for column in FLOAT_COLUMNS if column in prepared_frame.columns],
        }
        return len(prepared_frame)
