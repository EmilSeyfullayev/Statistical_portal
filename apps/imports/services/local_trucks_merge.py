from dataclasses import dataclass

from django.db import connection

from apps.imports.services.truck_routes import (
    fromto_from_sql_expression,
    fromto_to_sql_expression,
)

LOCAL_TRUCKS_SCHEMA = "local_trucks"
MERGED_TABLE = "local_trucks_merged"
SOURCE_TABLE_PREFIX = "local_trucks_"
NUMERIC_COLUMNS = {
    "source_row_number",
    "import_job_id",
    "IDN",
    "CODE",
    "CONCESSION_CODE",
    "PERMISSION_PRICE",
    "DIRECTION",
    "TESDIQ",
    "CONTROL_ST",
    "STATUS",
}
FLOAT_COLUMNS = {
    "WEIGHT",
    "TOTAL_WEIGHT",
    "WIDTH",
    "HEIGHT",
    "WEIGHT_PER_AX",
    "PLACE_WHEEL_COUNT",
}
TIMESTAMP_COLUMNS = {"imported_at", "DATESIGN", "ENTER_DATE"}
EXCLUDED_SOURCE_TABLES = {MERGED_TABLE}


@dataclass(frozen=True)
class LocalTrucksMergeResult:
    source_table_count: int
    merged_row_count: int
    merged_table: str


def quote_name(name):
    return connection.ops.quote_name(name)


def qualified_name(schema, table):
    return f"{quote_name(schema)}.{quote_name(table)}"


def source_tables(cursor):
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
          AND table_name LIKE %s
          AND table_name <> ALL(%s)
        ORDER BY table_name
        """,
        [LOCAL_TRUCKS_SCHEMA, f"{SOURCE_TABLE_PREFIX}%", list(EXCLUDED_SOURCE_TABLES)],
    )
    return [row[0] for row in cursor.fetchall()]


def table_columns(cursor, tables):
    if not tables:
        return {}
    cursor.execute(
        """
        SELECT table_name, column_name, data_type, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = ANY(%s)
        ORDER BY table_name, ordinal_position
        """,
        [LOCAL_TRUCKS_SCHEMA, tables],
    )
    columns_by_table = {table: [] for table in tables}
    for table_name, column_name, data_type, _ordinal_position in cursor.fetchall():
        columns_by_table[table_name].append((column_name, data_type))
    return columns_by_table


def merged_columns(columns_by_table):
    seen = set()
    columns = []
    for table_columns_list in columns_by_table.values():
        for column_name, _data_type in table_columns_list:
            if column_name not in seen:
                seen.add(column_name)
                columns.append(column_name)
                if column_name == "FROMTO":
                    for route_column in ["FROM", "TO"]:
                        if route_column not in seen:
                            seen.add(route_column)
                            columns.append(route_column)
    return columns


def merged_type_for(column_name):
    if column_name in TIMESTAMP_COLUMNS:
        return "timestamp with time zone"
    if column_name in FLOAT_COLUMNS:
        return "double precision"
    if column_name in NUMERIC_COLUMNS:
        return "bigint"
    return "text"


def timestamp_cast_expression(column_name, data_type):
    quoted_column = quote_name(column_name)
    if data_type == "timestamp with time zone":
        return f"{quoted_column}::timestamp with time zone"
    trimmed = f"NULLIF(btrim({quoted_column}::text), '')"
    return (
        "CASE "
        f"WHEN {trimmed} IS NULL THEN NULL "
        f"ELSE to_timestamp({trimmed}, 'DD.MM.YYYY HH24:MI:SS') "
        "END"
    )


def numeric_cast_expression(column_name, target_type):
    quoted_column = quote_name(column_name)
    trimmed = f"NULLIF(btrim({quoted_column}::text), '')"
    if target_type == "bigint":
        pattern = r"^[-+]?[0-9]+$"
    else:
        pattern = r"^[-+]?([0-9]+([.][0-9]*)?|[.][0-9]+)$"
    return (
        "CASE "
        f"WHEN {trimmed} IS NULL THEN NULL "
        f"WHEN {trimmed} ~ '{pattern}' THEN {trimmed}::{target_type} "
        "ELSE NULL "
        "END"
    )


def cast_expression(column_name, data_type):
    quoted_column = quote_name(column_name)
    target_type = merged_type_for(column_name)
    if target_type == "text":
        return f"{quoted_column}::text"
    if target_type == "timestamp with time zone":
        return timestamp_cast_expression(column_name, data_type)
    return numeric_cast_expression(column_name, target_type)


def select_sql_for_table(table, columns, table_column_map):
    source_columns = {column_name: data_type for column_name, data_type in table_column_map}
    select_parts = []
    for column in columns:
        if column == "FROM" and "FROMTO" in source_columns:
            expression = fromto_from_sql_expression(cast_expression("FROMTO", source_columns["FROMTO"]))
        elif column == "TO" and "FROMTO" in source_columns:
            expression = fromto_to_sql_expression(cast_expression("FROMTO", source_columns["FROMTO"]))
        elif column in source_columns:
            expression = cast_expression(column, source_columns[column])
        else:
            expression = f"NULL::{merged_type_for(column)}"
        select_parts.append(f"{expression} AS {quote_name(column)}")
    return f"SELECT {', '.join(select_parts)} FROM {qualified_name(LOCAL_TRUCKS_SCHEMA, table)}"


def create_merged_table(cursor, tables, columns_by_table):
    columns = merged_columns(columns_by_table)
    merged_columns_sql = ", ".join(
        f"{quote_name(column)} {merged_type_for(column)}" for column in columns
    )
    cursor.execute(f"DROP TABLE IF EXISTS {qualified_name(LOCAL_TRUCKS_SCHEMA, MERGED_TABLE)}")
    cursor.execute(
        f"CREATE TABLE {qualified_name(LOCAL_TRUCKS_SCHEMA, MERGED_TABLE)} "
        f"({merged_columns_sql})"
    )
    union_sql = "\nUNION ALL\n".join(
        select_sql_for_table(table, columns, columns_by_table[table]) for table in tables
    )
    cursor.execute(
        f"INSERT INTO {qualified_name(LOCAL_TRUCKS_SCHEMA, MERGED_TABLE)} "
        f"SELECT * FROM ({union_sql}) merged_source"
    )
    if "ENTER_DATE" in columns:
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{MERGED_TABLE}_enter_date_idx')} "
            f"ON {qualified_name(LOCAL_TRUCKS_SCHEMA, MERGED_TABLE)} ({quote_name('ENTER_DATE')} DESC NULLS LAST)"
        )
    if "DATESIGN" in columns:
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{MERGED_TABLE}_datesign_idx')} "
            f"ON {qualified_name(LOCAL_TRUCKS_SCHEMA, MERGED_TABLE)} ({quote_name('DATESIGN')} DESC NULLS LAST)"
        )
    for column in ["CUST_NAME", "SHORT_NAME", "FROMTO", "HES_NAME"]:
        if column in columns:
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {quote_name(f'{MERGED_TABLE}_{column.lower()}_idx')} "
                f"ON {qualified_name(LOCAL_TRUCKS_SCHEMA, MERGED_TABLE)} ({quote_name(column)})"
            )


def rebuild_local_trucks_merged():
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_name(LOCAL_TRUCKS_SCHEMA)}")
        tables = source_tables(cursor)
        if not tables:
            cursor.execute(f"DROP TABLE IF EXISTS {qualified_name(LOCAL_TRUCKS_SCHEMA, MERGED_TABLE)}")
            return LocalTrucksMergeResult(
                source_table_count=0,
                merged_row_count=0,
                merged_table=f"{LOCAL_TRUCKS_SCHEMA}.{MERGED_TABLE}",
            )
        columns_by_table = table_columns(cursor, tables)
        create_merged_table(cursor, tables, columns_by_table)
        cursor.execute(f"SELECT count(*) FROM {qualified_name(LOCAL_TRUCKS_SCHEMA, MERGED_TABLE)}")
        row_count = cursor.fetchone()[0]
    return LocalTrucksMergeResult(
        source_table_count=len(tables),
        merged_row_count=row_count,
        merged_table=f"{LOCAL_TRUCKS_SCHEMA}.{MERGED_TABLE}",
    )
