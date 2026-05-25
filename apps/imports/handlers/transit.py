import csv
import io
import re
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.imports.base import BaseImporter


TRACE_COLUMNS = {
    "source_file_path",
    "source_sheet_name",
    "source_row_number",
    "import_job_id",
    "imported_at",
}
TRANSIT_SCHEMA = "transit"
DATE_COLUMNS = {"giris_tarixi", "cixis_tarixi"}
US_DATE_TEXT_PATTERN = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
COLUMN_ALIASES = {
    "mal_barkodu": "goods_id",
}


def normalize_identifier(value, *, default):
    normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", str(value).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        normalized = default
    if normalized[0].isdigit():
        normalized = f"_{normalized}"
    return normalized[:63]


def unique_identifier(value, used, *, default):
    base = normalize_identifier(value, default=default)
    base = COLUMN_ALIASES.get(base, base)
    candidate = base
    counter = 2
    while candidate in used or candidate in TRACE_COLUMNS:
        suffix = f"_{counter}"
        candidate = f"{base[: 63 - len(suffix)]}{suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def transit_table_name(path):
    upload_root = Path(settings.SYNC_DESTINATION_DIR).resolve()
    file_path = Path(path).resolve()
    try:
        relative_path = file_path.relative_to(upload_root)
    except ValueError:
        relative_path = Path(file_path.name)
    table_stem = relative_path.with_suffix("").as_posix()
    table_source = table_stem if table_stem.startswith("transit/") else f"transit/{table_stem}"
    return normalize_identifier(table_source, default="transit_file")


def sheet_name_for(path):
    workbook = pd.ExcelFile(path)
    return workbook.sheet_names[0]


def prepare_frame(frame, stored_file, job, sheet_name):
    frame = frame.copy()
    used_columns = set()
    column_mapping = {}
    renamed_columns = []

    for index, column in enumerate(frame.columns, start=1):
        normalized = unique_identifier(column, used_columns, default=f"column_{index}")
        column_mapping[normalized] = str(column)
        renamed_columns.append(normalized)

    frame.columns = renamed_columns
    frame = frame.where(pd.notnull(frame), None)
    frame.insert(0, "source_file_path", stored_file.server_path)
    frame.insert(1, "source_sheet_name", sheet_name)
    frame.insert(2, "source_row_number", range(2, len(frame) + 2))
    frame.insert(3, "import_job_id", job.id)
    frame.insert(4, "imported_at", timezone.now())
    frame = normalize_date_columns(frame)
    return frame, column_mapping


def parse_transit_date_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()

    text = str(value).strip()
    if not text:
        return None
    if US_DATE_TEXT_PATTERN.fullmatch(text):
        return pd.to_datetime(text, format="%m/%d/%Y").to_pydatetime()
    raise ValueError(f"Unsupported transit date value: {value!r}")


def normalize_date_columns(frame):
    normalized = frame.copy()
    for column in DATE_COLUMNS:
        if column not in normalized.columns:
            continue
        normalized[column] = [parse_transit_date_value(value) for value in normalized[column]]
    return normalized


def sql_type_for(column, series):
    if column in DATE_COLUMNS:
        return "timestamp with time zone"
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
    value = clean_value(value)
    if value is None:
        return None
    return value


def create_table(cursor, table_name, frame):
    quoted_schema = connection.ops.quote_name(TRANSIT_SCHEMA)
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

    quoted_schema = connection.ops.quote_name(TRANSIT_SCHEMA)
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


class TransitExcelImporter(BaseImporter):
    parser_key = "transit_excel_v1"

    def import_rows(self, job):
        table_name = transit_table_name(self.stored_file.server_path)
        sheet_name = sheet_name_for(self.stored_file.server_path)
        frame = pd.read_excel(self.stored_file.server_path, sheet_name=sheet_name)
        prepared_frame, column_mapping = prepare_frame(frame, self.stored_file, job, sheet_name)

        with connection.cursor() as cursor:
            create_table(cursor, table_name, prepared_frame)
            insert_frame(cursor, table_name, prepared_frame)

        job.metadata = {
            **job.metadata,
            "generated_table": table_name,
            "generated_schema": TRANSIT_SCHEMA,
            "source_sheet": sheet_name,
            "column_mapping": column_mapping,
        }
        return len(prepared_frame)
