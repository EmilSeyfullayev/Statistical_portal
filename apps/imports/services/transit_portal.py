from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from django.db import connection

from apps.imports.services.transit_merge import TRANSIT_SCHEMA, quote_name, qualified_name

MERGED_TABLE = "transit_merged"
PORTAL_TABLE = "transit_data_for_portal"
DASHBOARD_TABLE = "transit_for_dashboard_on_ministry_portal"

RAW_COLUMNS: list[str] = [
    "GIRIS_TARIXI",
    "GIRIS_NV_NOVU",
    "GIRIS_GO",
    "GIRIS_DEHLIZ",
    "BOSALTMA_YUKLEME_GO",
    "CIXIS_TARIXI",
    "CIXIS_NV_NOVU",
    "CIXIS_GO",
    "CIXIS_DEHLIZ",
    "MAL_GONDEREN_OLKE",
    "MAL_TEYINAT_OLKE",
    "MAL_KODU",
    "MAL_CEKI_TON",
]

RAW_GROUP_COLUMNS: list[str] = [
    "GIRIS_TARIXI",
    "GIRIS_NV_NOVU",
    "GIRIS_GO",
    "GIRIS_DEHLIZ",
    "BOSALTMA_YUKLEME_GO",
    "CIXIS_TARIXI",
    "CIXIS_NV_NOVU",
    "CIXIS_GO",
    "CIXIS_DEHLIZ",
    "MAL_GONDEREN_OLKE",
    "MAL_TEYINAT_OLKE",
    "MAL_KODU",
]

RENAME_MAPPING: dict[str, str] = {
    "MAL_CEKI_TON": "Yük həcmi (ton)",
    "MAL_GONDEREN_OLKE": "Göndərən ölkə",
    "MAL_TEYINAT_OLKE": "Təyinat ölkə",
    "GIRIS_GO": "Gömrük giriş postu",
    "GIRIS_TARIXI": "Giriş tarixi",
    "GIRIS_NV_NOVU": "Giriş nəqliyyat növü",
    "GIRIS_DEHLIZ": "Giriş nöqtəsi",
    "BOSALTMA_YUKLEME_GO": "Boşaltma-yükləmə gömrük postu",
    "CIXIS_GO": "Gömrük çıxış postu",
    "CIXIS_TARIXI": "Çıxış tarixi",
    "CIXIS_NV_NOVU": "Çıxış nəqliyyat növü",
    "CIXIS_DEHLIZ": "Çıxış nöqtəsi",
}

FINAL_GROUP_COLUMNS: list[str] = [
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
]

DASHBOARD_COLUMNS: list[str] = [
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

DASHBOARD_GROUP_COLUMNS: list[str] = [
    column for column in DASHBOARD_COLUMNS if column != "Yük həcmi (ton)"
]

DEHLIZ_REPLACE_MAPPING: dict[str, str] = {
    "SERQ": "Şərq",
    "QERB": "Qərb",
    "CENUB": "Cənub",
    "SIMAL": "Şimal",
}

DEHLIZ_CANONICAL_MAPPING: dict[str, str] = {
    "Qərb-Şərq": "Şərq-Qərb",
    "Qərb-Şimal": "Şimal-Qərb",
    "Cənub-Şimal": "Şimal-Cənub",
    "Qərb-Cənub": "Cənub-Qərb",
    "Şərq-Cənub": "Cənub-Şərq",
    "Şərq-Şimal": "Şimal-Şərq",
}

TRANSPORT_PRIORITY: list[str] = ["DEMIRYOLU", "AVTOMOBIL", "STASIONAR", "HAVA", "DENIZ"]

TRANSPORT_DISPLAY_MAPPING: dict[str, str] = {
    "AVTOMOBIL": "Avtomobil",
    "DEMIRYOLU": "Dəmiryolu",
    "STASIONAR": "Boru",
    "DENIZ": "Dəniz",
    "HAVA": "Hava",
}

NAKHCHIVAN_ANY_POST_PATTERN = r"Sədərək|Şahtaxtı|Culfa"
NAKHCHIVAN_CENUB_POST_PATTERN = r"Şahtaxtı|Culfa"
NAKHCHIVAN_QERB_POST_PATTERN = r"Sədərək"

SOURCE_COLUMN_ALIASES: dict[str, str] = {
    column.lower(): column for column in RAW_COLUMNS
}


@dataclass(frozen=True)
class PortalRebuildResult:
    source_table: str
    portal_table: str
    source_row_count: int
    portal_row_count: int


@dataclass(frozen=True)
class DashboardRebuildResult:
    source_table: str
    dashboard_table: str
    source_row_count: int
    dashboard_row_count: int


class MissingColumnsError(ValueError):
    pass


def validate_required_columns(df: pd.DataFrame, required_columns: Sequence[str]) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise MissingColumnsError(
            "Source data is missing required columns: " + ", ".join(missing)
        )


def normalize_source_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.rename(columns=SOURCE_COLUMN_ALIASES)
    validate_required_columns(normalized, RAW_COLUMNS)
    return normalized


def normalize_corridor_point(value: Any) -> str:
    if pd.isna(value):
        return "Digər"

    text = str(value).strip()
    if not text:
        return "Digər"

    return DEHLIZ_REPLACE_MAPPING.get(text.upper(), text)


def normalize_transport_pair_value(value: Any) -> str:
    if pd.isna(value):
        return "Digər"

    parts = [part.strip() for part in str(value).strip().upper().split("-") if part.strip()]
    for transport_type in TRANSPORT_PRIORITY:
        if transport_type in parts:
            return transport_type
    return "Digər"


def normalize_mal_kodu_to_2digit(series: pd.Series) -> pd.Series:
    mal_kodu_numeric = pd.to_numeric(series, errors="coerce")
    valid_code_mask = (
        mal_kodu_numeric.notna()
        & mal_kodu_numeric.between(1, 99)
        & (mal_kodu_numeric % 1 == 0)
    )
    mal_kodu_2digit = pd.Series("Digər", index=series.index, dtype="object")
    mal_kodu_2digit.loc[valid_code_mask] = (
        mal_kodu_numeric.loc[valid_code_mask].astype(int).astype(str).str.zfill(2)
    )
    return mal_kodu_2digit


def build_goods_mapping(
    goods_data: Iterable[Mapping[str, Any]] | None,
) -> tuple[dict[str, str], dict[str, str]]:
    code_to_name: dict[str, str] = {}
    code_to_section: dict[str, str] = {}

    if not goods_data:
        return code_to_name, code_to_section

    for section_block in goods_data:
        section_raw = str(section_block.get("section", "Digər"))
        section_name = section_raw.split(" - ", 1)[-1].strip() or "Digər"

        for category in section_block.get("categories", []):
            code = str(category.get("code", "")).strip().zfill(2)
            name = str(category.get("name", "Digər")).strip() or "Digər"
            if code:
                code_to_name[code] = name
                code_to_section[code] = section_name

    return code_to_name, code_to_section


def load_default_goods_data() -> tuple[Any, Any]:
    from apps.imports.services.goods_nomenclature import goods_nomenclature_data
    from apps.imports.services.goods_nomenclature_short import goods_nomenclature_short_data

    return goods_nomenclature_data, goods_nomenclature_short_data


def select_and_prepare_raw_columns(df: pd.DataFrame) -> pd.DataFrame:
    source = normalize_source_columns(df)
    prepared = source.loc[:, RAW_COLUMNS].copy()
    prepared["MAL_CEKI_TON"] = pd.to_numeric(prepared["MAL_CEKI_TON"], errors="coerce").fillna(0)
    return prepared.groupby(RAW_GROUP_COLUMNS, dropna=False, as_index=False)["MAL_CEKI_TON"].sum()


def convert_date_columns(
    df: pd.DataFrame,
    columns: Sequence[str] = ("GIRIS_TARIXI", "CIXIS_TARIXI"),
    dayfirst: bool = False,
) -> pd.DataFrame:
    converted = df.copy()
    for column in columns:
        if column in converted.columns:
            converted[column] = pd.to_datetime(converted[column], errors="coerce", dayfirst=dayfirst)
    return converted


def add_corridor_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["GIRIS_DEHLIZ"] = result["GIRIS_DEHLIZ"].map(normalize_corridor_point)
    result["CIXIS_DEHLIZ"] = result["CIXIS_DEHLIZ"].map(normalize_corridor_point)
    result["Dəhliz (istiqamətlə)"] = (
        result["GIRIS_DEHLIZ"].astype(str) + "-" + result["CIXIS_DEHLIZ"].astype(str)
    )
    result["Dəhliz"] = np.where(
        result["Dəhliz (istiqamətlə)"].str.contains("Digər", na=False)
        | (result["GIRIS_DEHLIZ"] == result["CIXIS_DEHLIZ"]),
        "Digər",
        result["Dəhliz (istiqamətlə)"],
    )
    result["Dəhliz"] = result["Dəhliz"].replace(DEHLIZ_CANONICAL_MAPPING)

    stationary_exit_mask = (
        result["CIXIS_NV_NOVU"].fillna("").astype(str).str.strip().str.upper().eq("STASIONAR")
    )
    result.loc[stationary_exit_mask, "Dəhliz (istiqamətlə)"] = "Şərq-Qərb"
    result.loc[stationary_exit_mask, "Dəhliz"] = "Şərq-Qərb"
    return result


def add_transport_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    giris = result["GIRIS_NV_NOVU"].fillna("Digər").astype(str).str.strip().str.upper()
    cixis = result["CIXIS_NV_NOVU"].fillna("Digər").astype(str).str.strip().str.upper()
    result["Giriş-Çıxış nəqliyyat növü"] = giris + "-" + cixis
    result["Nəqliyyat növü"] = (
        result["Giriş-Çıxış nəqliyyat növü"]
        .map(normalize_transport_pair_value)
        .replace(TRANSPORT_DISPLAY_MAPPING)
    )
    return result


def add_goods_columns(
    df: pd.DataFrame,
    goods_data: Iterable[Mapping[str, Any]] | None = None,
    goods_short_data: Iterable[Mapping[str, Any]] | None = None,
) -> pd.DataFrame:
    result = df.copy()
    if goods_data is None or goods_short_data is None:
        goods_data, goods_short_data = load_default_goods_data()

    code_to_name, code_to_section = build_goods_mapping(goods_data)
    code_to_short_name, code_to_short_section = build_goods_mapping(goods_short_data)
    mal_kodu_2digit = normalize_mal_kodu_to_2digit(result["MAL_KODU"])

    result["Məhsulun adı"] = mal_kodu_2digit.map(code_to_name).fillna("Digər")
    result["Məhsul qrupu"] = mal_kodu_2digit.map(code_to_section).fillna("Digər")
    result["Məhsul adı (qısaldılmış)"] = mal_kodu_2digit.map(code_to_short_name).fillna("Digər")
    result["Məhsul qrupu (qısaldılmış)"] = (
        mal_kodu_2digit.map(code_to_short_section).fillna("Digər")
    )
    return result


def apply_nakhchivan_corridor_rules(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    giris_go = result["GIRIS_GO"].fillna("").astype(str)
    cixis_go = result["CIXIS_GO"].fillna("").astype(str)

    any_nakhchivan_post = giris_go.str.contains(
        NAKHCHIVAN_ANY_POST_PATTERN, case=False, na=False, regex=True
    ) | cixis_go.str.contains(NAKHCHIVAN_ANY_POST_PATTERN, case=False, na=False, regex=True)
    result.loc[any_nakhchivan_post, "Dəhliz"] = "Cənub-Qərb"

    giris_cenub = giris_go.str.contains(
        NAKHCHIVAN_CENUB_POST_PATTERN, case=False, na=False, regex=True
    )
    cixis_cenub = cixis_go.str.contains(
        NAKHCHIVAN_CENUB_POST_PATTERN, case=False, na=False, regex=True
    )
    giris_qerb = giris_go.str.contains(
        NAKHCHIVAN_QERB_POST_PATTERN, case=False, na=False, regex=True
    )
    cixis_qerb = cixis_go.str.contains(
        NAKHCHIVAN_QERB_POST_PATTERN, case=False, na=False, regex=True
    )
    result["Dəhliz (istiqamətlə)"] = np.select(
        [giris_cenub & cixis_qerb, giris_qerb & cixis_cenub],
        ["Cənub-Qərb", "Qərb-Cənub"],
        default=result["Dəhliz (istiqamətlə)"],
    )
    return result


def rename_portal_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=RENAME_MAPPING)


def add_country_pair_column(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["Başlangıc-Təyinat ölkəsi"] = (
        result["Göndərən ölkə"].fillna("Digər").astype(str).str.strip()
        + "-"
        + result["Təyinat ölkə"].fillna("Digər").astype(str).str.strip()
    )
    return result


def final_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    validate_required_columns(df, FINAL_GROUP_COLUMNS + ["Yük həcmi (ton)"])
    return df.groupby(FINAL_GROUP_COLUMNS, dropna=False, as_index=False)["Yük həcmi (ton)"].sum()


def process_transit_data(
    raw_df: pd.DataFrame,
    goods_data: Iterable[Mapping[str, Any]] | None = None,
    goods_short_data: Iterable[Mapping[str, Any]] | None = None,
    dayfirst: bool = False,
) -> pd.DataFrame:
    df = select_and_prepare_raw_columns(raw_df)
    df = convert_date_columns(df, dayfirst=dayfirst)
    df = add_corridor_columns(df)
    df = add_transport_columns(df)
    df = add_goods_columns(df, goods_data=goods_data, goods_short_data=goods_short_data)
    df = apply_nakhchivan_corridor_rules(df)
    df = rename_portal_columns(df)
    df = add_country_pair_column(df)
    return final_aggregate(df)


def read_merged_transit_frame() -> pd.DataFrame:
    columns_sql = ", ".join(quote_name(column) for column in SOURCE_COLUMN_ALIASES)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {columns_sql} FROM {qualified_name(TRANSIT_SCHEMA, MERGED_TABLE)}")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
    return pd.DataFrame(rows, columns=columns)


def portal_sql_type(column: str) -> str:
    if column == "Yük həcmi (ton)":
        return "double precision"
    if column in {"Giriş tarixi", "Çıxış tarixi"}:
        return "timestamp with time zone"
    return "text"


def clean_sql_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()
    return value


def replace_portal_table(df: pd.DataFrame) -> None:
    qualified_table = qualified_name(TRANSIT_SCHEMA, PORTAL_TABLE)
    column_definitions = ", ".join(
        f"{quote_name(column)} {portal_sql_type(column)}" for column in df.columns
    )
    quoted_columns = ", ".join(quote_name(column) for column in df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    rows = [
        tuple(clean_sql_value(value) for value in row)
        for row in df.itertuples(index=False, name=None)
    ]

    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_name(TRANSIT_SCHEMA)}")
        cursor.execute(f"DROP TABLE IF EXISTS {qualified_table}")
        cursor.execute(f"CREATE TABLE {qualified_table} ({column_definitions})")
        if rows:
            cursor.executemany(
                f"INSERT INTO {qualified_table} ({quoted_columns}) VALUES ({placeholders})",
                rows,
            )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{PORTAL_TABLE}_cixis_tarixi_idx')} "
            f"ON {qualified_table} ({quote_name('Çıxış tarixi')})"
        )


def dashboard_group_select_sql() -> str:
    group_columns = ", ".join(quote_name(column) for column in DASHBOARD_GROUP_COLUMNS)
    return (
        f"{group_columns}, "
        f"SUM(COALESCE({quote_name('Yük həcmi (ton)')}, 0))::double precision "
        f"AS {quote_name('Yük həcmi (ton)')}"
    )


def replace_dashboard_table() -> int:
    source_table = qualified_name(TRANSIT_SCHEMA, PORTAL_TABLE)
    dashboard_table = qualified_name(TRANSIT_SCHEMA, DASHBOARD_TABLE)
    group_columns = ", ".join(quote_name(column) for column in DASHBOARD_GROUP_COLUMNS)

    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_name(TRANSIT_SCHEMA)}")
        cursor.execute(f"DROP TABLE IF EXISTS {dashboard_table}")
        cursor.execute(
            f"""
            CREATE TABLE {dashboard_table} AS
            SELECT {dashboard_group_select_sql()}
            FROM {source_table}
            GROUP BY {group_columns}
            """
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{DASHBOARD_TABLE}_cixis_tarixi_idx')} "
            f"ON {dashboard_table} ({quote_name('Çıxış tarixi')})"
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{DASHBOARD_TABLE}_neqliyyat_idx')} "
            f"ON {dashboard_table} ({quote_name('Nəqliyyat növü')})"
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{DASHBOARD_TABLE}_dehliz_idx')} "
            f"ON {dashboard_table} ({quote_name('Dəhliz')})"
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{DASHBOARD_TABLE}_country_idx')} "
            f"ON {dashboard_table} ({quote_name('Göndərən ölkə')}, {quote_name('Təyinat ölkə')})"
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote_name(f'{DASHBOARD_TABLE}_product_group_idx')} "
            f"ON {dashboard_table} ({quote_name('Məhsul qrupu (qısaldılmış)')})"
        )
        cursor.execute(f"SELECT count(*) FROM {dashboard_table}")
        return cursor.fetchone()[0]


def rebuild_transit_data_for_portal(*, dayfirst: bool = False) -> PortalRebuildResult:
    source_df = read_merged_transit_frame()
    portal_df = process_transit_data(source_df, dayfirst=dayfirst)
    replace_portal_table(portal_df)
    return PortalRebuildResult(
        source_table=f"{TRANSIT_SCHEMA}.{MERGED_TABLE}",
        portal_table=f"{TRANSIT_SCHEMA}.{PORTAL_TABLE}",
        source_row_count=len(source_df),
        portal_row_count=len(portal_df),
    )


def rebuild_transit_dashboard_table() -> DashboardRebuildResult:
    source_table = qualified_name(TRANSIT_SCHEMA, PORTAL_TABLE)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {source_table}")
        source_row_count = cursor.fetchone()[0]
    dashboard_row_count = replace_dashboard_table()
    return DashboardRebuildResult(
        source_table=f"{TRANSIT_SCHEMA}.{PORTAL_TABLE}",
        dashboard_table=f"{TRANSIT_SCHEMA}.{DASHBOARD_TABLE}",
        source_row_count=source_row_count,
        dashboard_row_count=dashboard_row_count,
    )
