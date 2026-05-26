from datetime import date

from django.db import connection
from django.http import QueryDict
from django.utils import timezone

PAGE_SIZE = 100
DOWNLOAD_LIMIT = 500

TRANSIT_NATIVE_COLUMNS = [
    "goods_id",
    "giris_tarixi",
    "giris_nv_novu",
    "giris_go",
    "giris_dehliz",
    "bosaltma_yukleme_go",
    "cixis_tarixi",
    "cixis_nv_novu",
    "cixis_go",
    "cixis_dehliz",
    "mal_gonderen_olke",
    "mal_teyinat_olke",
    "mal_kodu",
    "mal_ceki_ton",
]

TRANSIT_FILTERS = {
    "date_from": "Giriş tarixi",
    "date_to": "Çıxış tarixi",
    "mal_gonderen_olke": "Mal göndərən ölkə",
    "mal_teyinat_olke": "Mal təyinat ölkə",
    "giris_dehliz": "Giriş dəhliz",
    "cixis_dehliz": "Çıxış dəhliz",
    "mal_kodu": "Mal kodu",
}

TRANSIT_FILTER_FIELDS = [
    {"name": "date_from", "label": "Giriş tarixi", "type": "date"},
    {"name": "date_to", "label": "Çıxış tarixi", "type": "date"},
    {"name": "mal_gonderen_olke", "label": "Mal göndərən ölkə", "type": "select"},
    {"name": "mal_teyinat_olke", "label": "Mal təyinat ölkə", "type": "select"},
    {"name": "giris_dehliz", "label": "Giriş dəhliz", "type": "select"},
    {"name": "cixis_dehliz", "label": "Çıxış dəhliz", "type": "select"},
    {"name": "mal_kodu", "label": "Mal kodu", "type": "select"},
]

TRANSIT_COLUMN_LABELS = {
    "goods_id": "Goods id",
    "giris_tarixi": "Giriş tarixi",
    "giris_nv_novu": "Giriş nv növü",
    "giris_go": "Giriş gö",
    "giris_dehliz": "Giriş dəhliz",
    "bosaltma_yukleme_go": "Boşaltma yükləmə gö",
    "cixis_tarixi": "Çıxış tarixi",
    "cixis_nv_novu": "Çıxış nv növü",
    "cixis_go": "Çıxış gö",
    "cixis_dehliz": "Çıxış dəhliz",
    "mal_gonderen_olke": "Mal göndərən ölkə",
    "mal_teyinat_olke": "Mal təyinat ölkə",
    "mal_kodu": "Mal kodu",
    "mal_ceki_ton": "Mal çəkisi ton",
}

DATE_COLUMNS = {"giris_tarixi", "cixis_tarixi"}

PORTAL_TABLE = "transit_data_for_portal"
PORTAL_SCHEMA = "transit"
DASHBOARD_TABLE = "transit_for_dashboard_on_ministry_portal"

PORTAL_COLUMNS = [
    "Giriş tarixi",
    "Giriş nəqliyyat növü",
    "Gömrük giriş postu",
    "Giriş nöqtəsi",
    "Boşaltma-yükləmə gömrük postu",
    "Çıxış tarixi",
    "Çıxış nəqliyyat növü",
    "Gömrük çıxış postu",
    "Çıxış nöqtəsi",
    "Göndərən ölkə",
    "Təyinat ölkə",
    "MAL_KODU",
    "Dəhliz (istiqamətlə)",
    "Dəhliz",
    "Giriş-Çıxış nəqliyyat növü",
    "Nəqliyyat növü",
    "Məhsulun adı",
    "Məhsul qrupu",
    "Məhsul adı (qısaldılmış)",
    "Məhsul qrupu (qısaldılmış)",
    "Başlangıc-Təyinat ölkəsi",
    "Yük həcmi (ton)",
]

PORTAL_FILTER_COLUMNS = {
    "date_from": "Giriş tarixi",
    "date_to": "Çıxış tarixi",
    "mal_gonderen_olke": "Göndərən ölkə",
    "mal_teyinat_olke": "Təyinat ölkə",
    "giris_dehliz": "Giriş nöqtəsi",
    "cixis_dehliz": "Çıxış nöqtəsi",
    "neqliyyat_novu": "Nəqliyyat növü",
    "mehsulun_adi": "Məhsul adı (qısaldılmış)",
    "mehsul_qrupu": "Məhsul qrupu (qısaldılmış)",
    "dehliz_istiqametle": "Dəhliz (istiqamətlə)",
    "dehliz": "Dəhliz",
}

PORTAL_FILTER_FIELDS = [
    {"name": "date_from", "label": "Giriş tarixi", "type": "date"},
    {"name": "date_to", "label": "Çıxış tarixi", "type": "date"},
    {"name": "mal_gonderen_olke", "label": "Göndərən ölkə", "type": "select"},
    {"name": "mal_teyinat_olke", "label": "Təyinat ölkə", "type": "select"},
    {"name": "giris_dehliz", "label": "Giriş nöqtəsi", "type": "select"},
    {"name": "cixis_dehliz", "label": "Çıxış nöqtəsi", "type": "select"},
    {"name": "dehliz_istiqametle", "label": "Dəhliz (istiqamətlə)", "type": "select"},
    {"name": "dehliz", "label": "Dəhliz", "type": "select"},
    {"name": "neqliyyat_novu", "label": "Nəqliyyat növü", "type": "select"},
    {"name": "mehsulun_adi", "label": "Məhsul adı (qısaldılmış)", "type": "select"},
    {"name": "mehsul_qrupu", "label": "Məhsul qrupu (qısaldılmış)", "type": "select"},
]

PORTAL_FILTERS = {field["name"]: field["label"] for field in PORTAL_FILTER_FIELDS}

PORTAL_DATE_COLUMNS = {"Giriş tarixi", "Çıxış tarixi"}
PORTAL_ORDER_COLUMN = "Çıxış tarixi"

DASHBOARD_COLUMNS = [
    "Gömrük giriş postu",
    "Çıxış tarixi",
    "Gömrük çıxış postu",
    "Göndərən ölkə",
    "Təyinat ölkə",
    "Dəhliz (istiqamətlə)",
    "Dəhliz",
    "Nəqliyyat növü",
    "Məhsul adı (qısaldılmış)",
    "Məhsul qrupu (qısaldılmış)",
    "Yük həcmi (ton)",
]

DASHBOARD_DEFAULT_TRANSPORTS = ["Avtomobil", "Dəmiryolu", "Hava"]
DASHBOARD_VALUE_COLUMN = "Yük həcmi (ton)"
DASHBOARD_DATE_COLUMN = "Çıxış tarixi"

DASHBOARD_FILTER_COLUMNS = {
    "date_from": DASHBOARD_DATE_COLUMN,
    "date_to": DASHBOARD_DATE_COLUMN,
    "neqliyyat_novu": "Nəqliyyat növü",
    "dehliz": "Dəhliz",
    "dehliz_istiqametle": "Dəhliz (istiqamətlə)",
    "mal_gonderen_olke": "Göndərən ölkə",
    "mal_teyinat_olke": "Təyinat ölkə",
    "mehsul_qrupu": "Məhsul qrupu (qısaldılmış)",
    "giris_go": "Gömrük giriş postu",
    "cixis_go": "Gömrük çıxış postu",
}

DASHBOARD_FILTER_FIELDS = [
    {"name": "date_from", "label": "Çıxış tarixi - başlanğıc", "type": "date"},
    {"name": "date_to", "label": "Çıxış tarixi - son", "type": "date"},
    {"name": "neqliyyat_novu", "label": "Nəqliyyat növü", "type": "multi_select"},
    {"name": "dehliz", "label": "Dəhliz", "type": "select"},
    {"name": "dehliz_istiqametle", "label": "Dəhliz (istiqamətlə)", "type": "select"},
    {"name": "mal_gonderen_olke", "label": "Göndərən ölkə", "type": "select"},
    {"name": "mal_teyinat_olke", "label": "Təyinat ölkə", "type": "select"},
    {"name": "mehsul_qrupu", "label": "Məhsul qrupu", "type": "select"},
    {"name": "giris_go", "label": "Gömrük giriş postu", "type": "select"},
    {"name": "cixis_go", "label": "Gömrük çıxış postu", "type": "select"},
]

REPORT_YEAR_CURRENT = 2025
REPORT_YEAR_PREVIOUS = 2024
REPORT_PARTIAL_CURRENT = 2026
REPORT_PARTIAL_PREVIOUS = 2025
REPORT_COMPLETED_MONTH = 4
REPORT_TOP_LIMIT = 10


def quote_name(name):
    return connection.ops.quote_name(name)


def enrich_filter_fields(field_defs, filters, filter_options):
    return [
        {
            **field,
            "value": filters.get(field["name"], ""),
            "options": filter_options.get(field["name"], []),
        }
        for field in field_defs
    ]


def get_available_transit_columns():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'transit'
              AND table_name = 'transit_merged'
            """
        )
        available = {row[0] for row in cursor.fetchall()}
    return [column for column in TRANSIT_NATIVE_COLUMNS if column in available]


def transit_filter_options(columns):
    option_columns = [
        "mal_gonderen_olke",
        "mal_teyinat_olke",
        "giris_dehliz",
        "cixis_dehliz",
        "mal_kodu",
    ]
    options = {}
    with connection.cursor() as cursor:
        for column in option_columns:
            if column not in columns:
                options[column] = []
                continue
            quoted_column = quote_name(column)
            cursor.execute(
                f"""
                SELECT DISTINCT {quoted_column}
                FROM transit.transit_merged
                WHERE {quoted_column} IS NOT NULL AND btrim({quoted_column}) <> ''
                ORDER BY {quoted_column}
                LIMIT 500
                """
            )
            options[column] = [row[0] for row in cursor.fetchall()]
    return options


def build_transit_where(filters, columns):
    clauses = []
    params = []
    if filters.get("date_from") and "giris_tarixi" in columns:
        clauses.append(f"{quote_name('giris_tarixi')}::date >= %s")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        if "merged_cixis_tarixi" in columns:
            clauses.append("merged_cixis_tarixi::date <= %s")
            params.append(filters["date_to"])
        elif "cixis_tarixi" in columns:
            clauses.append(f"{quote_name('cixis_tarixi')}::date <= %s")
            params.append(filters["date_to"])

    for column in [
        "mal_gonderen_olke",
        "mal_teyinat_olke",
        "giris_dehliz",
        "cixis_dehliz",
        "mal_kodu",
    ]:
        if column in columns and filters.get(column):
            clauses.append(f"{quote_name(column)} = %s")
            params.append(filters[column])
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def clean_page_number(value):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def transit_select_sql(columns):
    select_parts = []
    for column in columns:
        quoted_column = quote_name(column)
        if column in DATE_COLUMNS:
            select_parts.append(f"NULLIF(left({quoted_column}::text, 10), '') AS {quoted_column}")
        else:
            select_parts.append(quoted_column)
    return ", ".join(select_parts)


def transit_column_labels(columns):
    return [TRANSIT_COLUMN_LABELS.get(column, column) for column in columns]


def pagination_items(page, total_pages):
    pages = {1, total_pages}
    pages.update(range(max(1, page - 2), min(total_pages, page + 2) + 1))
    items = []
    previous = 0
    for page_number in sorted(pages):
        if page_number - previous > 1:
            items.append({"ellipsis": True})
        items.append({"number": page_number, "current": page_number == page})
        previous = page_number
    return items


def transit_rows(params, *, limit=PAGE_SIZE, offset=0):
    columns = get_available_transit_columns()
    filters = {key: params.get(key, "").strip() for key in TRANSIT_FILTERS}
    where_sql, query_params = build_transit_where(filters, columns)
    select_columns = transit_select_sql(columns)
    order_sql = "ORDER BY merged_cixis_tarixi DESC NULLS LAST"

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM transit.transit_merged
            {where_sql}
            {order_sql}
            LIMIT %s OFFSET %s
            """,
            [*query_params, limit, offset],
        )
        rows = [
            {"cells": row}
            for row in cursor.fetchall()
        ]
        cursor.execute(f"SELECT count(*) FROM transit.transit_merged {where_sql}", query_params)
        filtered_count = cursor.fetchone()[0]
    return columns, filters, rows, filtered_count


def get_transit_merged_context(params):
    page = clean_page_number(params.get("page"))
    offset = (page - 1) * PAGE_SIZE
    columns, filters, rows, filtered_count = transit_rows(params, limit=PAGE_SIZE, offset=offset)
    total_pages = max(1, (filtered_count + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > total_pages:
        page = total_pages
        offset = (page - 1) * PAGE_SIZE
        columns, filters, rows, filtered_count = transit_rows(params, limit=PAGE_SIZE, offset=offset)
    base_query = QueryDict(mutable=True)
    for key, value in filters.items():
        if value:
            base_query[key] = value
    download_query = base_query.copy()
    download_query["download"] = "xlsx"
    filter_options = transit_filter_options(columns)

    return {
        "columns": columns,
        "column_labels": transit_column_labels(columns),
        "rows": rows,
        "filters": filters,
        "filter_labels": TRANSIT_FILTERS,
        "filter_options": filter_options,
        "filter_fields": enrich_filter_fields(TRANSIT_FILTER_FIELDS, filters, filter_options),
        "filtered_count": filtered_count,
        "limit": PAGE_SIZE,
        "page": page,
        "total_pages": total_pages,
        "has_previous": page > 1,
        "has_next": page < total_pages,
        "previous_page": page - 1,
        "next_page": page + 1,
        "pagination_items": pagination_items(page, total_pages),
        "page_start": offset + 1 if filtered_count else 0,
        "page_end": min(offset + len(rows), filtered_count),
        "query_string": base_query.urlencode(),
        "download_query_string": download_query.urlencode(),
        "download_limit": DOWNLOAD_LIMIT,
        "eyebrow": "Transit database",
        "heading": "Raw Transit Data",
    }


def get_transit_download_rows(params):
    columns = get_available_transit_columns()
    filters = {key: params.get(key, "").strip() for key in TRANSIT_FILTERS}
    where_sql, query_params = build_transit_where(filters, columns)
    select_columns = transit_select_sql(columns)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM transit.transit_merged
            {where_sql}
            ORDER BY merged_cixis_tarixi DESC NULLS LAST
            LIMIT %s
            """,
            [*query_params, DOWNLOAD_LIMIT],
        )
        return transit_column_labels(columns), cursor.fetchall()


def get_available_portal_columns():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            """,
            [PORTAL_SCHEMA, PORTAL_TABLE],
        )
        available = {row[0] for row in cursor.fetchall()}
    return [column for column in PORTAL_COLUMNS if column in available]


def portal_filter_options(columns):
    option_keys = [
        field["name"]
        for field in PORTAL_FILTER_FIELDS
        if field["type"] == "select"
    ]
    options = {}
    qualified_table = f"{quote_name(PORTAL_SCHEMA)}.{quote_name(PORTAL_TABLE)}"
    with connection.cursor() as cursor:
        for key in option_keys:
            column = PORTAL_FILTER_COLUMNS[key]
            if column not in columns:
                options[key] = []
                continue
            quoted_column = quote_name(column)
            cursor.execute(
                f"""
                SELECT DISTINCT {quoted_column}
                FROM {qualified_table}
                WHERE {quoted_column} IS NOT NULL AND btrim({quoted_column}::text) <> ''
                ORDER BY {quoted_column}
                LIMIT 500
                """
            )
            options[key] = [row[0] for row in cursor.fetchall()]
    return options


def build_portal_where(filters, columns):
    clauses = []
    params = []
    entry_date = quote_name(PORTAL_FILTER_COLUMNS["date_from"])
    exit_date = quote_name(PORTAL_FILTER_COLUMNS["date_to"])
    if filters.get("date_from") and PORTAL_FILTER_COLUMNS["date_from"] in columns:
        clauses.append(f"{entry_date}::date >= %s")
        params.append(filters["date_from"])
    if filters.get("date_to") and PORTAL_FILTER_COLUMNS["date_to"] in columns:
        clauses.append(f"{exit_date}::date <= %s")
        params.append(filters["date_to"])

    for key, column in PORTAL_FILTER_COLUMNS.items():
        if key in {"date_from", "date_to"}:
            continue
        if column in columns and filters.get(key):
            clauses.append(f"{quote_name(column)} = %s")
            params.append(filters[key])
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def portal_select_sql(columns):
    select_parts = []
    for column in columns:
        quoted_column = quote_name(column)
        if column in PORTAL_DATE_COLUMNS:
            select_parts.append(f"NULLIF(left({quoted_column}::text, 10), '') AS {quoted_column}")
        else:
            select_parts.append(quoted_column)
    return ", ".join(select_parts)


def portal_column_labels(columns):
    return list(columns)


def portal_rows(params, *, limit=PAGE_SIZE, offset=0):
    columns = get_available_portal_columns()
    filters = {key: params.get(key, "").strip() for key in PORTAL_FILTERS}
    where_sql, query_params = build_portal_where(filters, columns)
    select_columns = portal_select_sql(columns)
    order_sql = f"ORDER BY {quote_name(PORTAL_ORDER_COLUMN)} DESC NULLS LAST"
    qualified_table = f"{quote_name(PORTAL_SCHEMA)}.{quote_name(PORTAL_TABLE)}"

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM {qualified_table}
            {where_sql}
            {order_sql}
            LIMIT %s OFFSET %s
            """,
            [*query_params, limit, offset],
        )
        rows = [{"cells": row} for row in cursor.fetchall()]
        cursor.execute(f"SELECT count(*) FROM {qualified_table} {where_sql}", query_params)
        filtered_count = cursor.fetchone()[0]
    return columns, filters, rows, filtered_count


def get_transit_portal_context(params):
    page = clean_page_number(params.get("page"))
    offset = (page - 1) * PAGE_SIZE
    columns, filters, rows, filtered_count = portal_rows(params, limit=PAGE_SIZE, offset=offset)
    total_pages = max(1, (filtered_count + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > total_pages:
        page = total_pages
        offset = (page - 1) * PAGE_SIZE
        columns, filters, rows, filtered_count = portal_rows(params, limit=PAGE_SIZE, offset=offset)
    base_query = QueryDict(mutable=True)
    for key, value in filters.items():
        if value:
            base_query[key] = value
    download_query = base_query.copy()
    download_query["download"] = "xlsx"
    filter_options = portal_filter_options(columns)

    return {
        "columns": columns,
        "column_labels": portal_column_labels(columns),
        "rows": rows,
        "filters": filters,
        "filter_labels": PORTAL_FILTERS,
        "filter_options": filter_options,
        "filter_fields": enrich_filter_fields(PORTAL_FILTER_FIELDS, filters, filter_options),
        "filtered_count": filtered_count,
        "limit": PAGE_SIZE,
        "page": page,
        "total_pages": total_pages,
        "has_previous": page > 1,
        "has_next": page < total_pages,
        "previous_page": page - 1,
        "next_page": page + 1,
        "pagination_items": pagination_items(page, total_pages),
        "page_start": offset + 1 if filtered_count else 0,
        "page_end": min(offset + len(rows), filtered_count),
        "query_string": base_query.urlencode(),
        "download_query_string": download_query.urlencode(),
        "download_limit": DOWNLOAD_LIMIT,
        "eyebrow": "Transit portal database",
        "heading": "Processed Transit Data",
    }


def get_transit_portal_download_rows(params):
    columns = get_available_portal_columns()
    filters = {key: params.get(key, "").strip() for key in PORTAL_FILTERS}
    where_sql, query_params = build_portal_where(filters, columns)
    select_columns = portal_select_sql(columns)
    qualified_table = f"{quote_name(PORTAL_SCHEMA)}.{quote_name(PORTAL_TABLE)}"
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM {qualified_table}
            {where_sql}
            ORDER BY {quote_name(PORTAL_ORDER_COLUMN)} DESC NULLS LAST
            LIMIT %s
            """,
            [*query_params, DOWNLOAD_LIMIT],
        )
        return portal_column_labels(columns), cursor.fetchall()


def dashboard_qualified_table():
    return f"{quote_name(PORTAL_SCHEMA)}.{quote_name(DASHBOARD_TABLE)}"


def dashboard_table_exists():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
            )
            """,
            [PORTAL_SCHEMA, DASHBOARD_TABLE],
        )
        return cursor.fetchone()[0]


def getlist_param(params, key):
    if hasattr(params, "getlist"):
        values = params.getlist(key)
    else:
        value = params.get(key, "")
        values = value if isinstance(value, list) else [value]
    return [str(value).strip() for value in values if str(value).strip()]


def dashboard_filters(params):
    filters = {}
    for field in DASHBOARD_FILTER_FIELDS:
        key = field["name"]
        if field["type"] == "multi_select":
            values = getlist_param(params, key)
            filters[key] = values or list(DASHBOARD_DEFAULT_TRANSPORTS)
        else:
            filters[key] = params.get(key, "").strip()
    return filters


def dashboard_filter_options():
    option_fields = [
        field for field in DASHBOARD_FILTER_FIELDS if field["type"] in {"select", "multi_select"}
    ]
    options = {}
    qualified_table = dashboard_qualified_table()
    with connection.cursor() as cursor:
        for field in option_fields:
            key = field["name"]
            column = DASHBOARD_FILTER_COLUMNS[key]
            quoted_column = quote_name(column)
            cursor.execute(
                f"""
                SELECT DISTINCT {quoted_column}
                FROM {qualified_table}
                WHERE {quoted_column} IS NOT NULL AND btrim({quoted_column}::text) <> ''
                ORDER BY {quoted_column}
                LIMIT 500
                """
            )
            values = [row[0] for row in cursor.fetchall()]
            if key == "neqliyyat_novu":
                preferred = [value for value in DASHBOARD_DEFAULT_TRANSPORTS if value in values]
                others = [value for value in values if value not in DASHBOARD_DEFAULT_TRANSPORTS]
                values = preferred + others
            options[key] = values
    return options


def dashboard_filter_fields(filters, options):
    fields = []
    for field in DASHBOARD_FILTER_FIELDS:
        value = filters.get(field["name"], [] if field["type"] == "multi_select" else "")
        fields.append(
            {
                **field,
                "value": value,
                "options": options.get(field["name"], []),
            }
        )
    return fields


def append_in_clause(clauses, params, column, values):
    values = [value for value in values if value]
    if not values:
        return
    placeholders = ", ".join(["%s"] * len(values))
    clauses.append(f"{quote_name(column)} IN ({placeholders})")
    params.extend(values)


def build_dashboard_where(filters, *, include_date=True):
    clauses = []
    params = []
    if include_date:
        if filters.get("date_from"):
            clauses.append(f"{quote_name(DASHBOARD_DATE_COLUMN)}::date >= %s")
            params.append(filters["date_from"])
        if filters.get("date_to"):
            clauses.append(f"{quote_name(DASHBOARD_DATE_COLUMN)}::date <= %s")
            params.append(filters["date_to"])

    append_in_clause(
        clauses,
        params,
        DASHBOARD_FILTER_COLUMNS["neqliyyat_novu"],
        filters.get("neqliyyat_novu", []),
    )
    for key, column in DASHBOARD_FILTER_COLUMNS.items():
        if key in {"date_from", "date_to", "neqliyyat_novu"}:
            continue
        if filters.get(key):
            clauses.append(f"{quote_name(column)} = %s")
            params.append(filters[key])
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def fetch_dashboard_totals(filters):
    where_sql, params = build_dashboard_where(filters)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision,
                COUNT(*),
                MIN({quote_name(DASHBOARD_DATE_COLUMN)}::date),
                MAX({quote_name(DASHBOARD_DATE_COLUMN)}::date)
            FROM {dashboard_qualified_table()}
            {where_sql}
            """,
            params,
        )
        total_weight, row_count, min_date, max_date = cursor.fetchone()
    return {
        "total_weight": float(total_weight or 0),
        "row_count": row_count,
        "date_min": min_date,
        "date_max": max_date,
    }


def fetch_grouped_chart(filters, column, *, limit=8, include_date=True):
    where_sql, params = build_dashboard_where(filters, include_date=include_date)
    quoted_column = quote_name(column)
    extra_where = f"{quoted_column} IS NOT NULL AND btrim({quoted_column}::text) <> ''"
    if where_sql:
        where_sql = f"{where_sql} AND {extra_where}"
    else:
        where_sql = f"WHERE {extra_where}"
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {quoted_column}, COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision AS value
            FROM {dashboard_qualified_table()}
            {where_sql}
            GROUP BY {quoted_column}
            ORDER BY value DESC
            LIMIT %s
            """,
            [*params, limit],
        )
        rows = cursor.fetchall()
    return {
        "labels": [row[0] for row in rows],
        "values": [float(row[1] or 0) for row in rows],
    }


def fetch_yearly_trend(filters):
    where_sql, params = build_dashboard_where(filters)
    date_present_clause = f"{quote_name(DASHBOARD_DATE_COLUMN)} IS NOT NULL"
    if where_sql:
        where_sql = f"{where_sql} AND {date_present_clause}"
    else:
        where_sql = f"WHERE {date_present_clause}"
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                EXTRACT(YEAR FROM {quote_name(DASHBOARD_DATE_COLUMN)})::int AS year,
                COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision AS value
            FROM {dashboard_qualified_table()}
            {where_sql}
            GROUP BY year
            ORDER BY year
            """,
            params,
        )
        rows = cursor.fetchall()
    return {
        "labels": [str(row[0]) for row in rows],
        "values": [float(row[1] or 0) for row in rows],
    }


def fetch_pair_chart(filters, from_column, to_column, *, limit=8):
    where_sql, params = build_dashboard_where(filters)
    from_expr = f"COALESCE(NULLIF(btrim({quote_name(from_column)}::text), ''), 'Digər')"
    to_expr = f"COALESCE(NULLIF(btrim({quote_name(to_column)}::text), ''), 'Digər')"
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                {from_expr} AS source,
                {to_expr} AS target,
                COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision AS value
            FROM {dashboard_qualified_table()}
            {where_sql}
            GROUP BY source, target
            ORDER BY value DESC
            LIMIT %s
            """,
            [*params, limit],
        )
        rows = cursor.fetchall()
    return {
        "labels": [f"{row[0]} -> {row[1]}" for row in rows],
        "sources": [row[0] for row in rows],
        "targets": [row[1] for row in rows],
        "values": [float(row[2] or 0) for row in rows],
    }


def period_total(filters, start_date, end_date):
    where_sql, params = build_dashboard_where(filters, include_date=False)
    date_clause = f"{quote_name(DASHBOARD_DATE_COLUMN)}::date >= %s AND {quote_name(DASHBOARD_DATE_COLUMN)}::date < %s"
    if where_sql:
        where_sql = f"{where_sql} AND {date_clause}"
    else:
        where_sql = f"WHERE {date_clause}"
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision
            FROM {dashboard_qualified_table()}
            {where_sql}
            """,
            [*params, start_date, end_date],
        )
        return float(cursor.fetchone()[0] or 0)


def percent_change(current_value, previous_value):
    if not previous_value:
        return None
    return ((current_value - previous_value) / previous_value) * 100


def format_tons(value):
    return f"{value:,.0f}".replace(",", " ")


def build_comparison_card(title, current_label, previous_label, current_value, previous_value):
    change = percent_change(current_value, previous_value)
    if change is None:
        direction = "neutral"
        change_label = "Müqayisə üçün əvvəlki dövr yoxdur"
    else:
        direction = "up" if change >= 0 else "down"
        sign = "+" if change >= 0 else ""
        change_label = f"{sign}{change:.1f}%"
    return {
        "title": title,
        "current_label": current_label,
        "previous_label": previous_label,
        "current_value": format_tons(current_value),
        "previous_value": format_tons(previous_value),
        "change_label": change_label,
        "direction": direction,
    }


def dashboard_comparison_cards(filters):
    period_metrics = dashboard_period_metrics(filters)
    annual = period_metrics["annual"]
    cards = [
        build_comparison_card(
            "İllik müqayisə",
            annual["label"],
            annual["previous_label"],
            annual["value"],
            annual["previous_value"],
        )
    ]

    monthly = period_metrics.get("monthly")
    if monthly:
        cards.append(
            build_comparison_card(
                "Cari ilin tamamlanmış ayları",
                monthly["label"],
                monthly["previous_label"],
                monthly["value"],
                monthly["previous_value"],
            )
        )
    return cards


def dashboard_period_metrics(filters):
    now = timezone.localdate()
    last_completed_year = now.year - 1
    previous_year = last_completed_year - 1
    last_completed_year_total = period_total(
        filters,
        date(last_completed_year, 1, 1),
        date(last_completed_year + 1, 1, 1),
    )
    previous_year_total = period_total(
        filters,
        date(previous_year, 1, 1),
        date(previous_year + 1, 1, 1),
    )
    metrics = {
        "annual": {
            "title": "Son tamamlanmış il",
            "label": str(last_completed_year),
            "start_date": date(last_completed_year, 1, 1),
            "end_date": date(last_completed_year + 1, 1, 1),
            "value": last_completed_year_total,
            "value_label": format_tons(last_completed_year_total),
            "previous_label": str(previous_year),
            "previous_value": previous_year_total,
        }
    }
    completed_month = now.month - 1
    if now.month != 12 and completed_month > 0:
        current_period_total = period_total(
            filters,
            date(now.year, 1, 1),
            date(now.year, completed_month + 1, 1),
        )
        previous_period_total = period_total(
            filters,
            date(now.year - 1, 1, 1),
            date(now.year - 1, completed_month + 1, 1),
        )
        metrics["monthly"] = {
            "title": "Cari tamamlanmış dövr",
            "label": f"{now.year} Yan-{completed_month:02d}",
            "start_date": date(now.year, 1, 1),
            "end_date": date(now.year, completed_month + 1, 1),
            "value": current_period_total,
            "value_label": format_tons(current_period_total),
            "previous_label": f"{now.year - 1} Yan-{completed_month:02d}",
            "previous_value": previous_period_total,
        }
    return metrics


def dashboard_period_chart_filters(filters, period_metrics):
    period = period_metrics.get("monthly") or period_metrics["annual"]
    period_filters = {**filters}
    period_filters["date_from"] = period["start_date"].isoformat()
    period_filters["date_to"] = period["end_date"].isoformat()
    return period_filters, period["label"]


def get_transit_dashboard_context(params):
    if not dashboard_table_exists():
        return {
            "available": False,
            "message": (
                "Dashboard table is not available yet. Run "
                "`python manage.py rebuild_transit_dashboard_table` after rebuilding processed transit data."
            ),
        }

    filters = dashboard_filters(params)
    options = dashboard_filter_options()
    totals = fetch_dashboard_totals(filters)
    period_metrics = dashboard_period_metrics(filters)
    period_filters, chart_period_label = dashboard_period_chart_filters(filters, period_metrics)
    corridor_chart = fetch_grouped_chart(period_filters, "Dəhliz", limit=8)
    product_chart = fetch_grouped_chart(period_filters, "Məhsul qrupu (qısaldılmış)", limit=8)
    transport_chart = fetch_grouped_chart(period_filters, "Nəqliyyat növü", limit=8)
    country_flow = fetch_pair_chart(period_filters, "Göndərən ölkə", "Təyinat ölkə", limit=8)
    post_flow = fetch_pair_chart(period_filters, "Gömrük giriş postu", "Gömrük çıxış postu", limit=8)

    return {
        "available": True,
        "filters": filters,
        "filter_fields": dashboard_filter_fields(filters, options),
        "default_transports": DASHBOARD_DEFAULT_TRANSPORTS,
        "summary": {
            **totals,
            "row_count_label": format_tons(totals["row_count"]),
            "top_corridor": corridor_chart["labels"][0] if corridor_chart["labels"] else "Yoxdur",
            "top_product_group": product_chart["labels"][0] if product_chart["labels"] else "Yoxdur",
            "period_metrics": period_metrics,
            "chart_period_label": chart_period_label,
        },
        "comparison_cards": dashboard_comparison_cards(filters),
        "charts": {
            "yearlyTrend": {
                "type": "line",
                "title": "İllik trend",
                **fetch_yearly_trend(filters),
            },
            "transport": {
                "type": "bar",
                "title": "Nəqliyyat növü üzrə",
                **transport_chart,
            },
            "corridor": {
                "type": "bar",
                "title": "Dəhlizlər üzrə",
                **corridor_chart,
            },
            "productGroup": {
                "type": "donut",
                "title": "Məhsul qrupları",
                **product_chart,
            },
            "countryFlow": {
                "type": "flow",
                "title": "Ölkə axını",
                **country_flow,
            },
            "postFlow": {
                "type": "bar",
                "title": "Gömrük postu cütlükləri",
                **post_flow,
            },
        },
    }


def report_period_total(column, value, start_date, end_date):
    transport_placeholders = ", ".join(["%s"] * len(DASHBOARD_DEFAULT_TRANSPORTS))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision
            FROM {dashboard_qualified_table()}
            WHERE {quote_name(column)} = %s
              AND {quote_name('Nəqliyyat növü')} IN ({transport_placeholders})
              AND {quote_name(DASHBOARD_DATE_COLUMN)}::date >= %s
              AND {quote_name(DASHBOARD_DATE_COLUMN)}::date < %s
            """,
            [value, *DASHBOARD_DEFAULT_TRANSPORTS, start_date, end_date],
        )
        return float(cursor.fetchone()[0] or 0)


def report_total(start_date, end_date):
    transport_placeholders = ", ".join(["%s"] * len(DASHBOARD_DEFAULT_TRANSPORTS))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision
            FROM {dashboard_qualified_table()}
            WHERE {quote_name('Nəqliyyat növü')} IN ({transport_placeholders})
              AND {quote_name(DASHBOARD_DATE_COLUMN)}::date >= %s
              AND {quote_name(DASHBOARD_DATE_COLUMN)}::date < %s
            """,
            [*DASHBOARD_DEFAULT_TRANSPORTS, start_date, end_date],
        )
        return float(cursor.fetchone()[0] or 0)


def report_total_for_values(column, values, start_date, end_date):
    placeholders = ", ".join(["%s"] * len(values))
    transport_placeholders = ", ".join(["%s"] * len(DASHBOARD_DEFAULT_TRANSPORTS))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision
            FROM {dashboard_qualified_table()}
            WHERE {quote_name(column)} IN ({placeholders})
              AND {quote_name('Nəqliyyat növü')} IN ({transport_placeholders})
              AND {quote_name(DASHBOARD_DATE_COLUMN)}::date >= %s
              AND {quote_name(DASHBOARD_DATE_COLUMN)}::date < %s
            """,
            [*values, *DASHBOARD_DEFAULT_TRANSPORTS, start_date, end_date],
        )
        return float(cursor.fetchone()[0] or 0)


def report_top_values(column, start_date, end_date, *, limit=8, preferred_values=None):
    if preferred_values:
        return preferred_values

    quoted_column = quote_name(column)
    transport_placeholders = ", ".join(["%s"] * len(DASHBOARD_DEFAULT_TRANSPORTS))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {quoted_column}, COALESCE(SUM({quote_name(DASHBOARD_VALUE_COLUMN)}), 0)::double precision AS value
            FROM {dashboard_qualified_table()}
            WHERE {quote_name('Nəqliyyat növü')} IN ({transport_placeholders})
              AND {quote_name(DASHBOARD_DATE_COLUMN)}::date >= %s
              AND {quote_name(DASHBOARD_DATE_COLUMN)}::date < %s
              AND {quoted_column} IS NOT NULL
              AND btrim({quoted_column}::text) <> ''
            GROUP BY {quoted_column}
            ORDER BY value DESC
            LIMIT %s
            """,
            [*DASHBOARD_DEFAULT_TRANSPORTS, start_date, end_date, limit],
        )
        return [row[0] for row in cursor.fetchall()]


def to_thousand_tons(value):
    return value / 1000


def report_percent_change(current_value, previous_value):
    if not previous_value:
        return None
    return ((current_value - previous_value) / previous_value) * 100


def format_report_number(value):
    return f"{to_thousand_tons(value):,.1f}"


def format_report_percent(value):
    if value is None:
        return "-"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.0f}%"


def build_report_row(label, values):
    annual_current = values["annual_current"]
    annual_previous = values["annual_previous"]
    partial_current = values["partial_current"]
    partial_previous = values["partial_previous"]
    annual_change = report_percent_change(annual_current, annual_previous)
    partial_change = report_percent_change(partial_current, partial_previous)
    return {
        "label": label,
        "annual_previous": format_report_number(annual_previous),
        "annual_current": format_report_number(annual_current),
        "partial_previous": format_report_number(partial_previous),
        "partial_current": format_report_number(partial_current),
        "annual_change": annual_change,
        "partial_change": partial_change,
        "dynamic": format_report_percent(partial_change),
        "dynamic_direction": "up" if (partial_change or 0) >= 0 else "down",
    }


def report_rows_for_dimension(column, *, limit=8, preferred_values=None):
    annual_previous_start = date(REPORT_YEAR_PREVIOUS, 1, 1)
    annual_previous_end = date(REPORT_YEAR_PREVIOUS + 1, 1, 1)
    annual_current_start = date(REPORT_YEAR_CURRENT, 1, 1)
    annual_current_end = date(REPORT_YEAR_CURRENT + 1, 1, 1)
    partial_previous_start = date(REPORT_PARTIAL_PREVIOUS, 1, 1)
    partial_previous_end = date(REPORT_PARTIAL_PREVIOUS, REPORT_COMPLETED_MONTH + 1, 1)
    partial_current_start = date(REPORT_PARTIAL_CURRENT, 1, 1)
    partial_current_end = date(REPORT_PARTIAL_CURRENT, REPORT_COMPLETED_MONTH + 1, 1)

    labels = report_top_values(
        column,
        partial_current_start,
        partial_current_end,
        limit=limit,
        preferred_values=preferred_values,
    )
    rows = []
    for label in labels:
        rows.append(
            build_report_row(
                label,
                {
                    "annual_previous": report_period_total(column, label, annual_previous_start, annual_previous_end),
                    "annual_current": report_period_total(column, label, annual_current_start, annual_current_end),
                    "partial_previous": report_period_total(column, label, partial_previous_start, partial_previous_end),
                    "partial_current": report_period_total(column, label, partial_current_start, partial_current_end),
                },
            )
        )
    return rows


def report_summary_totals():
    annual_previous_start = date(REPORT_YEAR_PREVIOUS, 1, 1)
    annual_previous_end = date(REPORT_YEAR_PREVIOUS + 1, 1, 1)
    annual_current_start = date(REPORT_YEAR_CURRENT, 1, 1)
    annual_current_end = date(REPORT_YEAR_CURRENT + 1, 1, 1)
    partial_previous_start = date(REPORT_PARTIAL_PREVIOUS, 1, 1)
    partial_previous_end = date(REPORT_PARTIAL_PREVIOUS, REPORT_COMPLETED_MONTH + 1, 1)
    partial_current_start = date(REPORT_PARTIAL_CURRENT, 1, 1)
    partial_current_end = date(REPORT_PARTIAL_CURRENT, REPORT_COMPLETED_MONTH + 1, 1)
    values = {
        "annual_previous": report_total(annual_previous_start, annual_previous_end),
        "annual_current": report_total(annual_current_start, annual_current_end),
        "partial_previous": report_total(partial_previous_start, partial_previous_end),
        "partial_current": report_total(partial_current_start, partial_current_end),
    }
    return build_report_row("Total", values)


def report_summary_totals_for_values(column, values):
    annual_previous_start = date(REPORT_YEAR_PREVIOUS, 1, 1)
    annual_previous_end = date(REPORT_YEAR_PREVIOUS + 1, 1, 1)
    annual_current_start = date(REPORT_YEAR_CURRENT, 1, 1)
    annual_current_end = date(REPORT_YEAR_CURRENT + 1, 1, 1)
    partial_previous_start = date(REPORT_PARTIAL_PREVIOUS, 1, 1)
    partial_previous_end = date(REPORT_PARTIAL_PREVIOUS, REPORT_COMPLETED_MONTH + 1, 1)
    partial_current_start = date(REPORT_PARTIAL_CURRENT, 1, 1)
    partial_current_end = date(REPORT_PARTIAL_CURRENT, REPORT_COMPLETED_MONTH + 1, 1)
    values_map = {
        "annual_previous": report_total_for_values(column, values, annual_previous_start, annual_previous_end),
        "annual_current": report_total_for_values(column, values, annual_current_start, annual_current_end),
        "partial_previous": report_total_for_values(column, values, partial_previous_start, partial_previous_end),
        "partial_current": report_total_for_values(column, values, partial_current_start, partial_current_end),
    }
    return build_report_row("Total", values_map)


def report_sentence(row, period="partial"):
    value_key = "partial_current" if period == "partial" else "annual_current"
    change_key = "partial_change" if period == "partial" else "annual_change"
    change = row[change_key]
    sign = "+" if (change or 0) >= 0 else ""
    return {
        "label": row["label"],
        "value": row[value_key],
        "change": "-" if change is None else f"{sign}{change:.1f}%",
        "direction": "up" if (change or 0) >= 0 else "down",
    }


def get_transit_dynamics_report_context():
    if not dashboard_table_exists():
        return {
            "available": False,
            "message": (
                "Hesabat cədvəli hazır deyil. Əvvəlcə transit_for_dashboard_on_ministry_portal "
                "cədvəlini yenidən yaradın."
            ),
        }

    transport_rows = report_rows_for_dimension(
        "Nəqliyyat növü",
        preferred_values=DASHBOARD_DEFAULT_TRANSPORTS,
    )
    corridor_rows = report_rows_for_dimension("Dəhliz", limit=REPORT_TOP_LIMIT)
    product_rows = report_rows_for_dimension("Məhsul adı (qısaldılmış)", limit=REPORT_TOP_LIMIT)
    sender_country_rows = report_rows_for_dimension("Göndərən ölkə", limit=REPORT_TOP_LIMIT)
    destination_country_rows = report_rows_for_dimension("Təyinat ölkə", limit=REPORT_TOP_LIMIT)
    total_row = report_summary_totals_for_values("Nəqliyyat növü", DASHBOARD_DEFAULT_TRANSPORTS)

    return {
        "available": True,
        "unit": "min tonla",
        "annual_years": {"previous": REPORT_YEAR_PREVIOUS, "current": REPORT_YEAR_CURRENT},
        "partial_years": {
            "previous": f"{REPORT_PARTIAL_PREVIOUS}*",
            "current": f"{REPORT_PARTIAL_CURRENT}*",
            "label": f"{REPORT_PARTIAL_CURRENT}-cı ilin ilk {REPORT_COMPLETED_MONTH} ayında",
        },
        "transport": {
            "rows": transport_rows,
            "total": total_row,
            "annual_sentence": report_sentence(total_row, period="annual"),
            "partial_sentence": report_sentence(total_row, period="partial"),
            "bullets_annual": [report_sentence(row, period="annual") for row in transport_rows],
            "bullets_partial": [report_sentence(row, period="partial") for row in transport_rows],
        },
        "corridors": {"rows": corridor_rows},
        "products": {"rows": product_rows},
        "sender_countries": {"rows": sender_country_rows},
        "destination_countries": {"rows": destination_country_rows},
    }
