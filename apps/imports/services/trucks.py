from dataclasses import dataclass

from django.db import connection

LOCAL_SCHEMA = "local_trucks"
LOCAL_MERGED_TABLE = "local_trucks_merged"
FOREIGN_SCHEMA = "foreign_trucks"
FOREIGN_MERGED_TABLE = "foreign_trucks_merged"
TRUCKS_SCHEMA = "trucks"
TRUCKS_TABLE = "trucks"
AGGREGATED_TABLE = "trucks_aggregated"

WEIGHT_COLUMN = "WEIGHT"
LOCAL_DEDUP_COLUMNS = ["IDN", "CODE"]
SOURCE_METADATA_COLUMNS = {
    "source_file_path",
    "source_sheet_name",
    "source_row_number",
    "import_job_id",
    "imported_at",
}
DERIVED_COLUMNS = {"CARRIER", "Loaded", "AVTO", "NO", "IN_OUT", "Regime"}
AGGREGATE_DROP_COLUMNS = {
    "ENTER_DATE",
    "DATESIGN",
    "CODE",
    "IDN",
    "AVTO_NO",
    "CONCESSION_CODE",
    "PERM_BLANK_NO",
    "PERMISSION_PRICE",
    "HES_NAME",
    "CONS_NAME",
    "TOTAL_WEIGHT",
    "WIDTH",
    "HEIGHT",
    "WEIGHT_PER_AX",
    "PLACE_WHEEL_COUNT",
    "Unnamed: 0",
    "TESDIQ",
    "CONTROL_ST",
    "STATUS",
    *SOURCE_METADATA_COLUMNS,
}


@dataclass(frozen=True)
class TrucksBuildResult:
    trucks_row_count: int
    aggregated_row_count: int
    trucks_table: str
    aggregated_table: str


def quote_name(name):
    return connection.ops.quote_name(name)


def qualified_name(schema, table):
    return f"{quote_name(schema)}.{quote_name(table)}"


def source_table_columns(cursor, schema, table):
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        [schema, table],
    )
    return [row[0] for row in cursor.fetchall()]


def source_table_column_types(cursor, schema, table):
    cursor.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        [schema, table],
    )
    return {column_name: data_type for column_name, data_type in cursor.fetchall()}


def assert_source_tables_exist(cursor):
    cursor.execute(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE (table_schema = %s AND table_name = %s)
           OR (table_schema = %s AND table_name = %s)
        """,
        [LOCAL_SCHEMA, LOCAL_MERGED_TABLE, FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE],
    )
    existing = {(schema, table) for schema, table in cursor.fetchall()}
    required = {
        (LOCAL_SCHEMA, LOCAL_MERGED_TABLE),
        (FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE),
    }
    missing = required - existing
    if missing:
        missing_names = ", ".join(f"{schema}.{table}" for schema, table in sorted(missing))
        raise RuntimeError(f"Missing required merged truck table(s): {missing_names}")


def ordered_union(first, second):
    seen = set()
    columns = []
    for column in [*first, *second]:
        if column not in seen and column not in DERIVED_COLUMNS:
            seen.add(column)
            columns.append(column)
    return columns


def sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


def select_for_column(column, available_columns, column_types, *, grouped=False):
    if column not in available_columns:
        return f"NULL::{column_types[column]} AS {quote_name(column)}"
    quoted = quote_name(column)
    if grouped and column == WEIGHT_COLUMN:
        return f"SUM({quoted}) AS {quoted}"
    if grouped and column in SOURCE_METADATA_COLUMNS:
        return f"MIN({quoted}) AS {quoted}"
    return quoted


def local_grouped_select_sql(columns, local_columns, column_types):
    local_column_set = set(local_columns)
    group_columns = [
        column
        for column in columns
        if column in local_column_set
        and column != WEIGHT_COLUMN
        and column not in SOURCE_METADATA_COLUMNS
    ]
    select_parts = [select_for_column(column, local_column_set, column_types, grouped=True) for column in columns]
    group_sql = ", ".join(quote_name(column) for column in group_columns)
    return (
        f"SELECT {', '.join(select_parts)} "
        f"FROM {qualified_name(LOCAL_SCHEMA, LOCAL_MERGED_TABLE)} "
        f"GROUP BY {group_sql}"
    )


def foreign_select_sql(columns, foreign_columns, column_types):
    foreign_column_set = set(foreign_columns)
    select_parts = [select_for_column(column, foreign_column_set, column_types) for column in columns]
    return f"SELECT {', '.join(select_parts)} FROM {qualified_name(FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE)}"


def local_dedup_order_sql(columns):
    order_parts = [f"{quote_name(column)} NULLS LAST" for column in LOCAL_DEDUP_COLUMNS]
    if "DATESIGN" in columns:
        order_parts.append(f"{quote_name('DATESIGN')} DESC NULLS LAST")
    if "ENTER_DATE" in columns:
        order_parts.append(f"{quote_name('ENTER_DATE')} DESC NULLS LAST")
    return ", ".join(order_parts)


def loaded_expression():
    return (
        "CASE "
        f"WHEN {quote_name('WEIGHT')} > 0 THEN 'loaded' "
        f"WHEN {quote_name('WEIGHT')} = 0 THEN 'unloaded' "
        "ELSE NULL "
        "END"
    )


def avto_expression():
    avto_no = quote_name("AVTO_NO")
    return (
        "CASE "
        f"WHEN {avto_no} IS NULL THEN NULL "
        f"WHEN strpos({avto_no}::text, ':-') > 0 THEN NULLIF(btrim(split_part({avto_no}::text, ':-', 1)), '') "
        f"ELSE NULLIF(btrim({avto_no}::text), '') "
        "END"
    )


def no_expression():
    avto_no = quote_name("AVTO_NO")
    return (
        "CASE "
        f"WHEN {avto_no} IS NULL THEN NULL "
        f"WHEN strpos({avto_no}::text, ':-') > 0 THEN NULLIF(btrim(substr({avto_no}::text, strpos({avto_no}::text, ':-') + 2)), '') "
        "ELSE NULL "
        "END"
    )


def in_out_expression():
    direction = quote_name("DIRECTION")
    return (
        "CASE "
        f"WHEN {direction} IN (1, 3) THEN 'in' "
        f"WHEN {direction} IN (2, 5) THEN 'out' "
        f"WHEN {direction} = 9 THEN 'domestic' "
        "ELSE NULL "
        "END"
    )


def regime_expression():
    fromto = quote_name("FROMTO")
    from_column = quote_name("FROM")
    to_column = quote_name("TO")
    in_out = quote_name("IN_OUT")
    azerbaijan = sql_literal("Azərbaycan")
    return (
        "CASE "
        f"WHEN {fromto} IS NULL OR {fromto}::text NOT ILIKE '%Azərbaycan%' THEN 'Transit' "
        f"WHEN {in_out} = 'in' AND btrim({to_column}::text) = {azerbaijan} THEN 'Import' "
        f"WHEN {in_out} = 'out' AND btrim({from_column}::text) = {azerbaijan} THEN 'Export' "
        f"WHEN {in_out} = 'domestic' AND btrim({from_column}::text) = {azerbaijan} "
        f"AND btrim({to_column}::text) = {azerbaijan} THEN 'Inter-territorial' "
        f"WHEN {in_out} = 'in' AND btrim({from_column}::text) = {azerbaijan} THEN 'Other' "
        f"WHEN {in_out} = 'out' AND btrim({to_column}::text) = {azerbaijan} THEN 'Other' "
        "ELSE 'Other' "
        "END"
    )


def build_trucks_table(cursor, columns, local_columns, foreign_columns, column_types):
    local_select = local_grouped_select_sql(columns, local_columns, column_types)
    foreign_select = foreign_select_sql(columns, foreign_columns, column_types)
    source_select_parts = ", ".join(quote_name(column) for column in columns)
    cursor.execute(f"DROP TABLE IF EXISTS {qualified_name(TRUCKS_SCHEMA, TRUCKS_TABLE)}")
    cursor.execute(
        f"""
        CREATE TABLE {qualified_name(TRUCKS_SCHEMA, TRUCKS_TABLE)} AS
        WITH local_grouped AS (
            {local_select}
        ),
        local_dedup AS (
            SELECT DISTINCT ON ({', '.join(quote_name(column) for column in LOCAL_DEDUP_COLUMNS)}) *
            FROM local_grouped
            ORDER BY {local_dedup_order_sql(columns)}
        ),
        combined AS (
            SELECT {source_select_parts}, 'Local'::text AS {quote_name('CARRIER')}
            FROM local_dedup
            UNION ALL
            SELECT {source_select_parts}, 'Foreign'::text AS {quote_name('CARRIER')}
            FROM ({foreign_select}) foreign_source
        ),
        enriched AS (
            SELECT
                *,
                {loaded_expression()} AS {quote_name('Loaded')},
                {avto_expression()} AS {quote_name('AVTO')},
                {no_expression()} AS {quote_name('NO')},
                {in_out_expression()} AS {quote_name('IN_OUT')}
            FROM combined
        )
        SELECT
            *,
            {regime_expression()} AS {quote_name('Regime')}
        FROM enriched
        """
    )
    create_trucks_indexes(cursor)


def create_trucks_indexes(cursor):
    table = qualified_name(TRUCKS_SCHEMA, TRUCKS_TABLE)
    for column in ["IDN", "CODE", "DATESIGN", "CARRIER", "Loaded", "IN_OUT", "Regime", "FROM", "TO"]:
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{TRUCKS_TABLE}_{column.lower()}_idx')} "
            f"ON {table} ({quote_name(column)})"
        )


def aggregate_columns(cursor):
    columns = source_table_columns(cursor, TRUCKS_SCHEMA, TRUCKS_TABLE)
    return [
        column
        for column in columns
        if column not in AGGREGATE_DROP_COLUMNS
        and column != WEIGHT_COLUMN
    ]


def build_aggregated_table(cursor):
    columns = aggregate_columns(cursor)
    prepared_columns = [
        column
        for column in columns
        if column not in {"YEAR", "MONTH", "COUNT"}
    ]
    select_parts = [quote_name(column) for column in prepared_columns]
    select_parts.extend([
        f"EXTRACT(YEAR FROM {quote_name('DATESIGN')})::integer AS {quote_name('YEAR')}",
        f"EXTRACT(MONTH FROM {quote_name('DATESIGN')})::integer AS {quote_name('MONTH')}",
        f"1::bigint AS {quote_name('COUNT')}",
        f"{quote_name(WEIGHT_COLUMN)} AS {quote_name(WEIGHT_COLUMN)}",
    ])
    group_columns = [*prepared_columns, "YEAR", "MONTH"]
    group_sql = ", ".join(quote_name(column) for column in group_columns)
    output_columns = ", ".join(quote_name(column) for column in group_columns)
    cursor.execute(f"DROP TABLE IF EXISTS {qualified_name(TRUCKS_SCHEMA, AGGREGATED_TABLE)}")
    cursor.execute(
        f"""
        CREATE TABLE {qualified_name(TRUCKS_SCHEMA, AGGREGATED_TABLE)} AS
        WITH prepared AS (
            SELECT {', '.join(select_parts)}
            FROM {qualified_name(TRUCKS_SCHEMA, TRUCKS_TABLE)}
        )
        SELECT
            {output_columns},
            SUM({quote_name(WEIGHT_COLUMN)}) AS {quote_name(WEIGHT_COLUMN)},
            SUM({quote_name('COUNT')}) AS {quote_name('COUNT')}
        FROM prepared
        GROUP BY {group_sql}
        """
    )
    create_aggregated_indexes(cursor)


def create_aggregated_indexes(cursor):
    table = qualified_name(TRUCKS_SCHEMA, AGGREGATED_TABLE)
    for column in ["YEAR", "MONTH", "CARRIER", "Loaded", "IN_OUT", "Regime", "FROM", "TO"]:
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{AGGREGATED_TABLE}_{column.lower()}_idx')} "
            f"ON {table} ({quote_name(column)})"
        )


def count_rows(cursor, schema, table):
    cursor.execute(f"SELECT count(*) FROM {qualified_name(schema, table)}")
    return cursor.fetchone()[0]


def rebuild_trucks():
    with connection.cursor() as cursor:
        assert_source_tables_exist(cursor)
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_name(TRUCKS_SCHEMA)}")
        cursor.execute(f"DROP TABLE IF EXISTS {qualified_name(TRUCKS_SCHEMA, AGGREGATED_TABLE)}")

        local_columns = source_table_columns(cursor, LOCAL_SCHEMA, LOCAL_MERGED_TABLE)
        foreign_columns = source_table_columns(cursor, FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE)
        local_column_types = source_table_column_types(cursor, LOCAL_SCHEMA, LOCAL_MERGED_TABLE)
        foreign_column_types = source_table_column_types(cursor, FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE)
        column_types = {**foreign_column_types, **local_column_types}
        columns = ordered_union(local_columns, foreign_columns)

        for required_column in [*LOCAL_DEDUP_COLUMNS, WEIGHT_COLUMN, "DATESIGN", "FROMTO", "FROM", "TO"]:
            if required_column not in columns:
                raise RuntimeError(f"Missing required truck column: {required_column}")

        build_trucks_table(cursor, columns, local_columns, foreign_columns, column_types)
        trucks_row_count = count_rows(cursor, TRUCKS_SCHEMA, TRUCKS_TABLE)

        build_aggregated_table(cursor)
        aggregated_row_count = count_rows(cursor, TRUCKS_SCHEMA, AGGREGATED_TABLE)

    return TrucksBuildResult(
        trucks_row_count=trucks_row_count,
        aggregated_row_count=aggregated_row_count,
        trucks_table=f"{TRUCKS_SCHEMA}.{TRUCKS_TABLE}",
        aggregated_table=f"{TRUCKS_SCHEMA}.{AGGREGATED_TABLE}",
    )
