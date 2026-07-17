import csv
import io
import re
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.imports.base import BaseImporter


FOREIGN_TRUCKS_SCHEMA = "foreign_trucks"
TRACE_COLUMNS = {
    "source_file_path",
    "source_sheet_name",
    "source_row_number",
    "import_job_id",
    "imported_at",
}
TEXT_FIX_COLUMNS = ["SHORT_NAME", "FROMTO", "AVTO_NO", "CUST_NAME", "HES_NAME", "CONS_NAME"]
DATETIME_COLUMNS = ["DATESIGN", "ENTER_DATE"]
FLOAT_COLUMNS = ["WEIGHT"]
DROP_UPLOAD_COLUMNS = {"Unnamed: 0"}


def drop_unwanted_upload_columns(frame):
    return frame.drop(columns=[column for column in DROP_UPLOAD_COLUMNS if column in frame.columns])

HES_NAME_REPLACEMENTS = {
    "Yüksüz giriş üçıün": "Yüksüz giriş üçün",
    "Yüksüz giriş üÇün": "Yüksüz giriş üçün",
    "Yüklü giriş, yüksüz çııxış və tranzit keçıid üçıün": "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün",
    "Yüklü giriş, yüksüz Çıxış və tranzit keçid üçün": "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün",
    "Yüklü giriş, yüksüzÇıxış və tranzit keçid üçün": "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün",
    "Yüklü giriş, yüksüz Çıxış və tranzit keÇid üÇün": "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün",
    "Yüklü giriş, yüksüzıxış və tranzit keçid üçün": "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün",
    "Yüklü giriş, yüksüzçıxış və tranzit keçid üçün": "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün",
    "Yüklənmə üçıün": "Yüklənmə üçün",
    "Yüklənmə üÇün": "Yüklənmə üçün",
    "Üçıüncü ölkəyə və ya üçıüncü ölkədən daşınmalar üçıün": "Üçüncü ölkəyə və ya üçüncü ölkədən daşınmalar üçün",
    "ÜÇüncü ölkəyə və ya üÇüncü ölkədən daşınmalar üÇün": "Üçüncü ölkəyə və ya üçüncü ölkədən daşınmalar üçün",
}
LOWERCASE_LETTERS = "a-zəğıöşü"
IN_WORD_CAPITAL_C_PATTERN = re.compile(rf"(?<=[{LOWERCASE_LETTERS}])Ç")
COUNTRY_TOKEN_REPLACEMENTS = {
    "çexiya": "Çexiya",
    "çin": "Çin",
    "çinin": "Çinin",
    "çili": "Çili",
}
COUNTRY_TOKEN_PATTERN = re.compile(r"(?:(?<=^)|(?<=-))(çexiya|çinin|çin|çili)(?=-|$| )")
COUNTRY_SPACING_REPLACEMENTS = {
    "SuriyaƏrəb Respublikası": "Suriya Ərəb Respublikası",
    "BirləşmişƏrəbƏmirlikləri": "Birləşmiş Ərəb Əmirlikləri",
}
COUNTRY_VALUE_REPLACEMENTS = {
    "İaq": "İraq",
    "çin əyaləti": "Çin əyaləti",
    "çinin əyaləti": "Çinin əyaləti",
}

SYMBOL_REPLACEMENTS = {
    "Ä±": "ı",
    "ÄŸ": "ğ",
    "É™": "ə",
    "Ã¼": "ü",
    "Ã¶": "ö",
    "ÅŸ": "ş",
    "Ã§": "ç",
    "Æ\x8f": "Ə",
    "Ãœ": "Ü",
    "Ã–": "Ö",
    "Å\x9e": "Ş",
    "Ã‡": "Ç",
    "Ä°": "İ",
    "\x8f": "",
    "\x9e": "",
}


def normalize_identifier(value, *, default):
    normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", str(value).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).lstrip("_")
    if not normalized:
        normalized = default
    if normalized[0].isdigit():
        normalized = f"_{normalized}"
    return normalized[:63]


def foreign_trucks_table_name(path):
    upload_root = Path(settings.SYNC_DESTINATION_DIR).resolve()
    file_path = Path(path).resolve()
    try:
        relative_path = file_path.relative_to(upload_root)
    except ValueError:
        relative_path = Path(file_path.name)
    table_stem = relative_path.with_suffix("").as_posix()
    table_source = table_stem if table_stem.startswith("foreign_trucks/") else f"foreign_trucks/{table_stem}"
    return normalize_identifier(table_source, default="foreign_trucks_file")


def sheet_name_for(path):
    workbook = pd.ExcelFile(path)
    return workbook.sheet_names[0]


def replace_bad_symbols(value):
    if not isinstance(value, str):
        return value
    for bad_symbol, replacement in SYMBOL_REPLACEMENTS.items():
        value = value.replace(bad_symbol, replacement)
    value = IN_WORD_CAPITAL_C_PATTERN.sub("ç", value)
    value = COUNTRY_TOKEN_PATTERN.sub(lambda match: COUNTRY_TOKEN_REPLACEMENTS[match.group(1)], value)
    for bad_country, replacement in COUNTRY_SPACING_REPLACEMENTS.items():
        value = value.replace(bad_country, replacement)
    for bad_country, replacement in COUNTRY_VALUE_REPLACEMENTS.items():
        value = value.replace(bad_country, replacement)
    return value



def normalize_hes_name_value(value):
    value = value.replace("ÜÇ", "Üç")
    value = value.replace("üÇ", "üç")
    value = value.replace("üçıün", "üçün")
    value = value.replace("üçıün", "üçün")
    value = value.replace("çııxış", "çıxış")
    value = value.replace("keçıid", "keçid")
    value = value.replace("yüksüzıxış", "yüksüz çıxış")
    value = value.replace("yüksüzçıxış", "yüksüz çıxış")
    value = value.replace("yüksüzÇıxış", "yüksüz çıxış")
    value = value.replace("yüksüz Çıxış", "yüksüz çıxış")
    value = value.replace("Çıxış", "çıxış")
    return HES_NAME_REPLACEMENTS.get(value.strip(), value)


def normalize_text_value(value, column):
    value = replace_bad_symbols(value)
    if column == "HES_NAME" and isinstance(value, str):
        value = normalize_hes_name_value(value)
    return value


def sample_has_bad_symbols(frame):
    sample = frame.head(10)
    present_columns = [column for column in TEXT_FIX_COLUMNS if column in sample.columns]
    for column in present_columns:
        values = sample[column].dropna()
        for value in values:
            if not isinstance(value, str):
                continue
            if any(bad_symbol in value for bad_symbol in SYMBOL_REPLACEMENTS):
                return True
    return False


def fix_text_columns(frame):
    fixed = drop_unwanted_upload_columns(frame).copy()
    for column in TEXT_FIX_COLUMNS:
        if column in fixed.columns:
            fixed[column] = fixed[column].map(lambda value, col=column: normalize_text_value(value, col))
    return fixed


def parse_datetime_column(series):
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series, format="%d.%m.%Y %H:%M:%S", errors="coerce")


def normalize_foreign_trucks_frame(frame):
    normalized = fix_text_columns(frame)
    for column in DATETIME_COLUMNS:
        if column in normalized.columns:
            normalized[column] = parse_datetime_column(normalized[column])
    for column in FLOAT_COLUMNS:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce").astype("float64")
    return normalized


def prepare_frame(frame, stored_file, job, sheet_name):
    prepared = normalize_foreign_trucks_frame(frame)
    original_columns = [str(column) for column in prepared.columns]
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
    quoted_schema = connection.ops.quote_name(FOREIGN_TRUCKS_SCHEMA)
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

    quoted_schema = connection.ops.quote_name(FOREIGN_TRUCKS_SCHEMA)
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


class ForeignTrucksExcelImporter(BaseImporter):
    parser_key = "foreign_trucks_excel_v1"

    def import_rows(self, job):
        table_name = foreign_trucks_table_name(self.stored_file.server_path)
        sheet_name = sheet_name_for(self.stored_file.server_path)
        frame = pd.read_excel(self.stored_file.server_path, sheet_name=sheet_name)
        had_bad_symbols_in_sample = sample_has_bad_symbols(frame)
        prepared_frame, original_columns = prepare_frame(frame, self.stored_file, job, sheet_name)

        with connection.cursor() as cursor:
            create_table(cursor, table_name, prepared_frame)
            insert_frame(cursor, table_name, prepared_frame)

        job.metadata = {
            **job.metadata,
            "generated_table": table_name,
            "generated_schema": FOREIGN_TRUCKS_SCHEMA,
            "source_sheet": sheet_name,
            "original_columns": original_columns,
            "text_symbol_sample_checked_rows": min(10, len(frame)),
            "text_symbol_fixes_applied": True,
            "bad_symbols_found_in_first_10_rows": had_bad_symbols_in_sample,
            "datetime_columns": [column for column in DATETIME_COLUMNS if column in prepared_frame.columns],
            "float_columns": [column for column in FLOAT_COLUMNS if column in prepared_frame.columns],
        }
        return len(prepared_frame)
