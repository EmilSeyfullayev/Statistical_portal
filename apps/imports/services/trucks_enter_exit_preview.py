from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.db import connection
from openpyxl import Workbook


LOCAL_SCHEMA = "local_trucks"
LOCAL_MERGED_TABLE = "local_trucks_merged"
FOREIGN_SCHEMA = "foreign_trucks"
FOREIGN_MERGED_TABLE = "foreign_trucks_merged"

DEFAULT_OUTPUT_PATH = Path("/tmp/trucks_enter_exit_in_one_line_2026_01_05.xlsx")
START_DATE = "2026-01-01"
END_DATE = "2026-06-01"
AZERBAIJAN = "Azərbaycan"

OUTPUT_COLUMNS = [
    "CODE",
    "CARRIER",
    "Rejim",
    "DATESIGN",
    "YEAR",
    "MONTH",
    "WEIGHT",
    "enter_DATESIGN",
    "enter_FROM",
    "enter_TO",
    "enter_DIRECTION",
    "enter_WEIGHT",
    "enter_CUST_NAME",
    "enter_AVTO_NO",
    "exit_DATESIGN",
    "exit_FROM",
    "exit_TO",
    "exit_DIRECTION",
    "exit_WEIGHT",
    "exit_CUST_NAME",
    "exit_AVTO_NO",
    "days_between",
]


@dataclass(frozen=True)
class TrucksEnterExitPreviewResult:
    output_path: str
    row_count: int
    regime_counts: dict
    min_datesign: object
    max_datesign: object
    entrance_only_count: int
    exit_only_count: int
    both_sides_count: int


def quote_name(name):
    return connection.ops.quote_name(name)


def qualified_name(schema, table):
    return f"{quote_name(schema)}.{quote_name(table)}"


def sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


def normalized_weight_sql(alias):
    weight = f"{alias}.{quote_name('WEIGHT')}"
    return f"CASE WHEN {weight} > 50000 THEN {weight} / 10 ELSE {weight} END"


def date_window_sql(alias):
    datesign = f"{alias}.{quote_name('DATESIGN')}"
    return f"{datesign} >= DATE {sql_literal(START_DATE)} AND {datesign} < DATE {sql_literal(END_DATE)}"


def non_empty_country_pair_sql(alias):
    from_column = f"{alias}.{quote_name('FROM')}"
    to_column = f"{alias}.{quote_name('TO')}"
    return (
        f"{from_column} IS NOT NULL AND btrim({from_column}::text) <> '' "
        f"AND {to_column} IS NOT NULL AND btrim({to_column}::text) <> ''"
    )


def is_azerbaijan_sql(alias, column):
    return f"btrim({alias}.{quote_name(column)}::text) = {sql_literal(AZERBAIJAN)}"


def is_not_azerbaijan_sql(alias, column):
    return f"btrim({alias}.{quote_name(column)}::text) <> {sql_literal(AZERBAIJAN)}"


def source_columns_sql(alias):
    return ",\n            ".join(
        [
            f"{alias}.{quote_name('CODE')} AS {quote_name('CODE')}",
            f"{alias}.{quote_name('DATESIGN')} AS {quote_name('DATESIGN')}",
            f"{alias}.{quote_name('FROM')} AS {quote_name('FROM')}",
            f"{alias}.{quote_name('TO')} AS {quote_name('TO')}",
            f"{alias}.{quote_name('DIRECTION')} AS {quote_name('DIRECTION')}",
            f"{alias}.{quote_name('WEIGHT')} AS {quote_name('WEIGHT')}",
            f"{alias}.{quote_name('CUST_NAME')} AS {quote_name('CUST_NAME')}",
            f"{alias}.{quote_name('AVTO_NO')} AS {quote_name('AVTO_NO')}",
        ]
    )


def side_columns_sql(alias, side):
    return ",\n            ".join(
        [
            f"{alias}.{quote_name('DATESIGN')} AS {quote_name(f'{side}_DATESIGN')}",
            f"{alias}.{quote_name('FROM')} AS {quote_name(f'{side}_FROM')}",
            f"{alias}.{quote_name('TO')} AS {quote_name(f'{side}_TO')}",
            f"{alias}.{quote_name('DIRECTION')} AS {quote_name(f'{side}_DIRECTION')}",
            f"{alias}.{quote_name('WEIGHT')} AS {quote_name(f'{side}_WEIGHT')}",
            f"{alias}.{quote_name('CUST_NAME')} AS {quote_name(f'{side}_CUST_NAME')}",
            f"{alias}.{quote_name('AVTO_NO')} AS {quote_name(f'{side}_AVTO_NO')}",
        ]
    )


def null_side_columns_sql(side):
    return ",\n            ".join(
        [
            f"NULL::timestamp AS {quote_name(f'{side}_DATESIGN')}",
            f"NULL::text AS {quote_name(f'{side}_FROM')}",
            f"NULL::text AS {quote_name(f'{side}_TO')}",
            f"NULL::integer AS {quote_name(f'{side}_DIRECTION')}",
            f"NULL::numeric AS {quote_name(f'{side}_WEIGHT')}",
            f"NULL::text AS {quote_name(f'{side}_CUST_NAME')}",
            f"NULL::text AS {quote_name(f'{side}_AVTO_NO')}",
        ]
    )


def preview_sql():
    local_table = qualified_name(LOCAL_SCHEMA, LOCAL_MERGED_TABLE)
    foreign_table = qualified_name(FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE)
    code = quote_name("CODE")
    idn = quote_name("IDN")
    datesign = quote_name("DATESIGN")
    source_projection = ", ".join(quote_name(column) for column in [
        "CODE",
        "DATESIGN",
        "FROM",
        "TO",
        "DIRECTION",
        "WEIGHT",
        "CUST_NAME",
        "AVTO_NO",
    ])
    local_group_columns = ["IDN", "CODE", "DATESIGN", "FROM", "TO", "DIRECTION", "CUST_NAME", "AVTO_NO"]
    local_group_sql = ", ".join(f"l.{quote_name(column)}" for column in local_group_columns)

    return f"""
    WITH local_grouped AS (
        SELECT
            {local_group_sql},
            SUM({normalized_weight_sql('l')}) AS "WEIGHT"
        FROM {local_table} l
        WHERE l.{datesign} IS NOT NULL
          AND {date_window_sql('l')}
          AND {non_empty_country_pair_sql('l')}
        GROUP BY {local_group_sql}
    ),
    local_dedup AS (
        SELECT DISTINCT ON ({idn}, {code})
            {source_projection}
        FROM local_grouped
        ORDER BY {idn} NULLS LAST, {code} NULLS LAST, {datesign} DESC NULLS LAST
    ),
    foreign_normalized AS (
        SELECT
            {source_columns_sql('f').replace('f."WEIGHT" AS "WEIGHT"', normalized_weight_sql('f') + ' AS "WEIGHT"')}
        FROM {foreign_table} f
        WHERE f.{datesign} IS NOT NULL
          AND {date_window_sql('f')}
          AND {non_empty_country_pair_sql('f')}
    ),
    source_rows AS (
        SELECT 'Local'::text AS "CARRIER", {source_projection} FROM local_dedup
        UNION ALL
        SELECT 'Foreign'::text AS "CARRIER", {source_projection} FROM foreign_normalized
    ),
    transit_enter AS (
        SELECT DISTINCT ON ({code})
            {code},
            "CARRIER",
            {side_columns_sql('e', 'enter')}
        FROM source_rows e
        WHERE (e."CARRIER" = 'Local' AND e."DIRECTION" = 3)
           OR (
                e."CARRIER" = 'Foreign'
                AND e."DIRECTION" = 1
                AND {is_not_azerbaijan_sql('e', 'FROM')}
                AND {is_not_azerbaijan_sql('e', 'TO')}
           )
        ORDER BY {code} NULLS LAST, e.{datesign} DESC NULLS LAST
    ),
    transit_exit AS (
        SELECT DISTINCT ON ({code})
            {code},
            "CARRIER",
            {side_columns_sql('x', 'exit')}
        FROM source_rows x
        WHERE (x."CARRIER" = 'Local' AND x."DIRECTION" = 5)
           OR (
                x."CARRIER" = 'Foreign'
                AND x."DIRECTION" = 2
                AND {is_not_azerbaijan_sql('x', 'FROM')}
                AND {is_not_azerbaijan_sql('x', 'TO')}
           )
        ORDER BY {code} NULLS LAST, x.{datesign} DESC NULLS LAST
    ),
    transit_rows AS (
        SELECT
            COALESCE(e.{code}, x.{code}) AS "CODE",
            COALESCE(e."CARRIER", x."CARRIER") AS "CARRIER",
            'Tranzit'::text AS "Rejim",
            COALESCE(x."exit_DATESIGN", e."enter_DATESIGN") AS "DATESIGN",
            COALESCE(x."exit_WEIGHT", e."enter_WEIGHT") AS "WEIGHT",
            e."enter_DATESIGN",
            e."enter_FROM",
            e."enter_TO",
            e."enter_DIRECTION",
            e."enter_WEIGHT",
            e."enter_CUST_NAME",
            e."enter_AVTO_NO",
            x."exit_DATESIGN",
            x."exit_FROM",
            x."exit_TO",
            x."exit_DIRECTION",
            x."exit_WEIGHT",
            x."exit_CUST_NAME",
            x."exit_AVTO_NO"
        FROM transit_enter e
        FULL OUTER JOIN transit_exit x ON e.{code} = x.{code}
    ),
    import_rows AS (
        SELECT DISTINCT ON ({code})
            {code} AS "CODE",
            "CARRIER",
            'İdxal'::text AS "Rejim",
            e."DATESIGN",
            e."WEIGHT",
            {side_columns_sql('e', 'enter')},
            {null_side_columns_sql('exit')}
        FROM source_rows e
        WHERE e."DIRECTION" = 1
          AND {is_azerbaijan_sql('e', 'FROM')}
        ORDER BY {code} NULLS LAST, e.{datesign} DESC NULLS LAST
    ),
    export_rows AS (
        SELECT DISTINCT ON ({code})
            {code} AS "CODE",
            "CARRIER",
            'İxrac'::text AS "Rejim",
            x."DATESIGN",
            x."WEIGHT",
            {null_side_columns_sql('enter')},
            {side_columns_sql('x', 'exit')}
        FROM source_rows x
        WHERE x."DIRECTION" = 2
          AND {is_azerbaijan_sql('x', 'TO')}
        ORDER BY {code} NULLS LAST, x.{datesign} DESC NULLS LAST
    ),
    domestic_rows AS (
        SELECT DISTINCT ON ({code})
            {code} AS "CODE",
            "CARRIER",
            'Daxili'::text AS "Rejim",
            d."DATESIGN",
            d."WEIGHT",
            {side_columns_sql('d', 'enter')},
            {null_side_columns_sql('exit')}
        FROM source_rows d
        WHERE d."DIRECTION" IN (8, 9)
        ORDER BY {code} NULLS LAST, d.{datesign} DESC NULLS LAST
    ),
    classified_rows AS (
        SELECT * FROM transit_rows
        UNION ALL
        SELECT * FROM import_rows
        UNION ALL
        SELECT * FROM export_rows
        UNION ALL
        SELECT * FROM domestic_rows
    )
    SELECT
        "CODE",
        "CARRIER",
        "Rejim",
        "DATESIGN",
        EXTRACT(YEAR FROM "DATESIGN")::integer AS "YEAR",
        EXTRACT(MONTH FROM "DATESIGN")::integer AS "MONTH",
        "WEIGHT",
        "enter_DATESIGN",
        "enter_FROM",
        "enter_TO",
        "enter_DIRECTION",
        "enter_WEIGHT",
        "enter_CUST_NAME",
        "enter_AVTO_NO",
        "exit_DATESIGN",
        "exit_FROM",
        "exit_TO",
        "exit_DIRECTION",
        "exit_WEIGHT",
        "exit_CUST_NAME",
        "exit_AVTO_NO",
        CASE
            WHEN "enter_DATESIGN" IS NOT NULL AND "exit_DATESIGN" IS NOT NULL
            THEN "exit_DATESIGN"::date - "enter_DATESIGN"::date
            ELSE NULL
        END AS "days_between"
    FROM classified_rows
    ORDER BY "Rejim", "CODE"
    """


def export_trucks_enter_exit_preview(output_path=DEFAULT_OUTPUT_PATH):
    rows = fetch_preview_rows()
    write_preview_workbook(output_path, rows)
    return preview_result(output_path, rows)


def fetch_preview_rows():
    with connection.cursor() as cursor:
        cursor.execute(preview_sql())
        return cursor.fetchall()


def write_preview_workbook(output_path, rows):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("trucks_enter_exit")
    sheet.append(OUTPUT_COLUMNS)
    for row in rows:
        sheet.append([excel_value(value) for value in row])
    workbook.save(output_path)


def preview_result(output_path, rows):
    regime_counts = {}
    min_datesign = None
    max_datesign = None
    entrance_only_count = 0
    exit_only_count = 0
    both_sides_count = 0

    for row in rows:
        data = dict(zip(OUTPUT_COLUMNS, row))
        regime_counts[data["Rejim"]] = regime_counts.get(data["Rejim"], 0) + 1

        datesign = data["DATESIGN"]
        if datesign is not None:
            min_datesign = datesign if min_datesign is None else min(min_datesign, datesign)
            max_datesign = datesign if max_datesign is None else max(max_datesign, datesign)

        has_enter = data["enter_DATESIGN"] is not None
        has_exit = data["exit_DATESIGN"] is not None
        if has_enter and has_exit:
            both_sides_count += 1
        elif has_enter:
            entrance_only_count += 1
        elif has_exit:
            exit_only_count += 1

    return TrucksEnterExitPreviewResult(
        output_path=str(output_path),
        row_count=len(rows),
        regime_counts=regime_counts,
        min_datesign=min_datesign,
        max_datesign=max_datesign,
        entrance_only_count=entrance_only_count,
        exit_only_count=exit_only_count,
        both_sides_count=both_sides_count,
    )


def excel_value(value):
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value
