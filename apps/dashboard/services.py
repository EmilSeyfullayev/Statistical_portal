from django.db import connection
from django.http import QueryDict

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
    "date_from": "Çıxış tarixi başlanğıc",
    "date_to": "Çıxış tarixi son",
    "mal_gonderen_olke": "Mal göndərən ölkə",
    "mal_teyinat_olke": "Mal təyinat ölkə",
    "giris_dehliz": "Giriş dəhliz",
    "cixis_dehliz": "Çıxış dəhliz",
    "mal_kodu": "Mal kodu",
}

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


def quote_name(name):
    return connection.ops.quote_name(name)


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
    if filters.get("date_from"):
        clauses.append("merged_cixis_tarixi::date >= %s")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("merged_cixis_tarixi::date <= %s")
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

    return {
        "columns": columns,
        "column_labels": transit_column_labels(columns),
        "rows": rows,
        "filters": filters,
        "filter_labels": TRANSIT_FILTERS,
        "filter_options": transit_filter_options(columns),
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
