import pandas as pd
from django.db import connection

from apps.imports.services.compas_point import add_compass_point_column


LOCAL_SCHEMA = "local_trucks"
LOCAL_MERGED_TABLE = "local_trucks_merged"
FOREIGN_SCHEMA = "foreign_trucks"
FOREIGN_MERGED_TABLE = "foreign_trucks_merged"

START_DATE = "2026-05-01"
END_DATE = "2026-06-01"
WEIGHT_COLUMN = "WEIGHT"
VEHICLE_TYPE_COLUMN = "Nəqliyyat növü"
VEHICLE_NUMBER_COLUMN = "Avto nömrəsi"
LOADED_EMPTY_COLUMN = "Yüklü-boş"
LOADED_VALUE = "Yüklü"
EMPTY_VALUE = "Boş"
CODE_COLUMN = "CODE"
DIRECTION_COLUMN = "DIRECTION"
FROM_COLUMN = "FROM"
TO_COLUMN = "TO"
REGIME_COLUMN = "Rejim"
OPERATION_COLUMN = "Əməliyyat"
AZERBAIJAN = "Azərbaycan"
DEDUP_COLUMNS = ["IDN", CODE_COLUMN]
DATESIGN_COLUMN = "DATESIGN"
CARRIER_COLUMN = "CARRIER"
CARRIER_AZ_COLUMN = "Daşıyıcı"
LOCAL_CARRIER_VALUE = "Yerli"
FOREIGN_CARRIER_VALUE = "Xarici"
DROP_OUTPUT_COLUMNS = [
    "source_file_path",
    "source_sheet_name",
    "source_row_number",
    "import_job_id",
    "imported_at",
    "FROMTO",
    "PLACE_WHEEL_COUNT",
    "WIDTH",
    "HEIGHT",
    "WEIGHT_PER_AX",
    "TESDIQ",
    "CONTROL_ST",
    "STATUS",
    CARRIER_COLUMN,
    "ENTER_DATE",
    "AVTO_NO",
]


def quote_name(name):
    return connection.ops.quote_name(name)


def qualified_name(schema, table):
    return f"{quote_name(schema)}.{quote_name(table)}"


def read_may_2026_merged_table(schema, table):
    # Only May 2026 rows are processed in this workflow.
    query = f"""
        SELECT *
        FROM {qualified_name(schema, table)}
        WHERE {quote_name(DATESIGN_COLUMN)} >= %s
          AND {quote_name(DATESIGN_COLUMN)} < %s
          AND {quote_name(CODE_COLUMN)} IS NOT NULL
          AND btrim({quote_name(CODE_COLUMN)}::text) <> ''
    """
    source_df = pd.read_sql_query(query, connection, params=[START_DATE, END_DATE])
    return normalize_weight_column(source_df)


def normalize_weight_column(source_df):
    # Values above 50000 are known data-entry mistakes and should be divided by 10
    # before local grouping or downstream calculations use WEIGHT.
    source_df = source_df.copy()
    weight = pd.to_numeric(source_df[WEIGHT_COLUMN], errors="coerce")
    source_df[WEIGHT_COLUMN] = weight.where(weight <= 50000, weight / 10)
    return source_df


def group_local_by_all_columns_except_weight(local_df):
    # Local merged rows can repeat with every value identical except WEIGHT.
    # Group by the full row identity and sum WEIGHT, keeping NA values as valid
    # group keys. This is the pandas equivalent of groupby(..., dropna=False).
    group_columns = [column for column in local_df.columns if column != WEIGHT_COLUMN]
    if not group_columns or WEIGHT_COLUMN not in local_df.columns:
        return local_df.copy()

    return (
        local_df.groupby(group_columns, dropna=False, as_index=False, sort=False)[WEIGHT_COLUMN]
        .sum()
    )


def align_columns(first_df, second_df):
    columns = [
        *first_df.columns,
        *[column for column in second_df.columns if column not in first_df.columns],
    ]
    return first_df.reindex(columns=columns), second_df.reindex(columns=columns)


def add_carrier_columns(source_df, carrier, carrier_az):
    # Daşıyıcı is the business-facing carrier label requested for this workflow.
    # CARRIER is kept as an internal English source label for compatibility with
    # existing truck-processing code.
    source_df = source_df.copy()
    source_df[CARRIER_COLUMN] = carrier
    source_df[CARRIER_AZ_COLUMN] = carrier_az
    return source_df


def add_loaded_empty_column(source_df):
    source_df = source_df.copy()
    weight = pd.to_numeric(source_df[WEIGHT_COLUMN], errors="coerce")
    source_df[LOADED_EMPTY_COLUMN] = EMPTY_VALUE
    source_df.loc[weight > 0, LOADED_EMPTY_COLUMN] = LOADED_VALUE
    return source_df


def split_vehicle_column(source_df):
    # AVTO_NO is stored as two values separated by ":-": vehicle type first,
    # vehicle number second. Whitespace around the separator can vary.
    source_df = source_df.copy()
    vehicle_parts = source_df["AVTO_NO"].astype("string").str.split(
        r"\s*:-\s*",
        n=1,
        expand=True,
    )
    source_df[VEHICLE_TYPE_COLUMN] = vehicle_parts[0].str.strip()
    source_df[VEHICLE_NUMBER_COLUMN] = (
        vehicle_parts[1].str.strip() if 1 in vehicle_parts.columns else pd.NA
    )
    return source_df


def clean_country_series(series):
    return series.astype("string").str.strip()


def is_exact_azerbaijan(series):
    return clean_country_series(series).eq(AZERBAIJAN)


def is_non_azerbaijan_country(series):
    country = clean_country_series(series)
    return country.notna() & country.ne("") & country.ne(AZERBAIJAN)


def correct_reversed_azerbaijan_routes(source_df):
    # Some rows are reversed around Azərbaycan. For direction 1, Azərbaycan must
    # be TO for an inbound movement; for direction 2, Azərbaycan must be FROM for
    # an outbound movement. Swap only exact Azərbaycan against another country.
    source_df = source_df.copy()
    direction = pd.to_numeric(source_df[DIRECTION_COLUMN], errors="coerce")
    from_is_azerbaijan = is_exact_azerbaijan(source_df[FROM_COLUMN])
    to_is_azerbaijan = is_exact_azerbaijan(source_df[TO_COLUMN])
    from_is_other_country = is_non_azerbaijan_country(source_df[FROM_COLUMN])
    to_is_other_country = is_non_azerbaijan_country(source_df[TO_COLUMN])

    swap_mask = (
        ((direction == 1) & from_is_azerbaijan & to_is_other_country)
        | ((direction == 2) & to_is_azerbaijan & from_is_other_country)
    )
    source_df.loc[swap_mask, [FROM_COLUMN, TO_COLUMN]] = source_df.loc[
        swap_mask,
        [TO_COLUMN, FROM_COLUMN],
    ].to_numpy()
    return source_df


def add_operation_column(source_df):
    # Əməliyyat is the simple movement direction label from DIRECTION.
    source_df = source_df.copy()
    direction = pd.to_numeric(source_df[DIRECTION_COLUMN], errors="coerce")
    source_df[OPERATION_COLUMN] = pd.NA
    source_df.loc[direction.isin([1, 3]), OPERATION_COLUMN] = "Giriş"
    source_df.loc[direction.isin([2, 5]), OPERATION_COLUMN] = "Çıxış"
    source_df.loc[direction.isin([8, 9]), OPERATION_COLUMN] = "Daxili"
    return source_df


def combine_local_and_foreign(local_df, foreign_df):
    local_df, foreign_df = align_columns(local_df, foreign_df)
    return pd.concat([local_df, foreign_df], ignore_index=True, sort=False)


def contains_azerbaijan(series):
    return series.astype("string").str.contains(AZERBAIJAN, case=False, na=False)


def add_regime_column(source_df):
    # Rejim depends on DIRECTION and whether Azərbaycan appears in FROM/TO.
    # Direction 1/2 can be transit, import/export, domestic, or other depending
    # on route; directions 3/5 are transit only when the route does not mention
    # Azərbaycan.
    source_df = source_df.copy()
    direction = pd.to_numeric(source_df[DIRECTION_COLUMN], errors="coerce")
    from_has_azerbaijan = contains_azerbaijan(source_df[FROM_COLUMN])
    to_has_azerbaijan = contains_azerbaijan(source_df[TO_COLUMN])
    any_azerbaijan = from_has_azerbaijan | to_has_azerbaijan
    no_azerbaijan = ~any_azerbaijan

    source_df[REGIME_COLUMN] = "Digər"
    source_df.loc[(direction == 3) & no_azerbaijan, REGIME_COLUMN] = "Tranzit giriş"
    source_df.loc[(direction == 5) & no_azerbaijan, REGIME_COLUMN] = "Tranzit çıxış"
    source_df.loc[(direction == 1) & no_azerbaijan, REGIME_COLUMN] = "Tranzit giriş"
    source_df.loc[(direction == 2) & no_azerbaijan, REGIME_COLUMN] = "Tranzit çıxış"
    source_df.loc[
        (direction == 1) & ~from_has_azerbaijan & to_has_azerbaijan,
        REGIME_COLUMN,
    ] = "İdxal"
    source_df.loc[
        (direction == 2) & from_has_azerbaijan & ~to_has_azerbaijan,
        REGIME_COLUMN,
    ] = "İxrac"
    source_df.loc[direction.isin([8, 9]), REGIME_COLUMN] = "Daxili"
    source_df.loc[
        direction.isin([1, 2]) & from_has_azerbaijan & to_has_azerbaijan,
        REGIME_COLUMN,
    ] = "Daxili (ölkədənkənar)"
    return source_df


def drop_output_columns(source_df):
    # Remove source metadata and technical columns from the final structured data.
    return source_df.drop(columns=DROP_OUTPUT_COLUMNS, errors="ignore")


def sort_by_datesign(combined_df):
    # Sort oldest to newest so "keep first" means the first registered movement.
    return combined_df.sort_values(
        DATESIGN_COLUMN,
        ascending=True,
        na_position="last",
        kind="mergesort",
    )


def drop_duplicate_idn_code_keep_first(sorted_df):
    # De-duplicate only where both IDN and CODE are present. Rows with missing
    # key values are kept because they cannot safely be proven to be duplicates.
    complete_key_mask = sorted_df[DEDUP_COLUMNS].notna().all(axis=1)
    complete_keys = sorted_df.loc[complete_key_mask]
    incomplete_keys = sorted_df.loc[~complete_key_mask]

    deduplicated_complete_keys = complete_keys.drop_duplicates(
        subset=DEDUP_COLUMNS,
        keep="first",
    )
    deduplicated_df = pd.concat([deduplicated_complete_keys, incomplete_keys]).sort_index(
        kind="mergesort",
    )
    return deduplicated_df.reset_index(drop=True)


def build_may_2026_enter_exit_in_one_line_source():
    # Step 1: read May 2026 data from the already merged local and foreign truck
    # sources. This function only returns structured data; it does not create or
    # generate any database table.
    local_df = add_carrier_columns(
        read_may_2026_merged_table(LOCAL_SCHEMA, LOCAL_MERGED_TABLE),
        "Local",
        LOCAL_CARRIER_VALUE,
    )
    foreign_df = add_carrier_columns(
        read_may_2026_merged_table(FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE),
        "Foreign",
        FOREIGN_CARRIER_VALUE,
    )

    # Step 2: before combining local and foreign data, consolidate local rows
    # that are identical except for WEIGHT.
    grouped_local_df = group_local_by_all_columns_except_weight(local_df)

    # Step 3: combine processed local rows with foreign rows into one dataset.
    combined_df = combine_local_and_foreign(grouped_local_df, foreign_df)

    # Step 4: split AVTO_NO into vehicle type and vehicle number columns.
    combined_df = split_vehicle_column(combined_df)

    # Step 5: correct reversed routes where Azərbaycan is on the wrong side for
    # direction 1 or 2. This correction runs before Rejim classification.
    combined_df = correct_reversed_azerbaijan_routes(combined_df)

    # Step 6: create the loaded/empty label from WEIGHT.
    combined_df = add_loaded_empty_column(combined_df)

    # Step 7: create the movement operation label from DIRECTION.
    combined_df = add_operation_column(combined_df)

    # Step 8: create the entry-exit compass point from CUST_NAME. Unknown
    # customs posts are marked as Digər.
    combined_df = add_compass_point_column(combined_df)

    # Step 9: classify each row into the requested Rejim categories.
    combined_df = add_regime_column(combined_df)

    # Step 10: sort by DATESIGN so the earliest registration is first.
    sorted_df = sort_by_datesign(combined_df)

    # Step 11: for repeated IDN + CODE pairs, keep the row registered first.
    deduplicated_df = drop_duplicate_idn_code_keep_first(sorted_df)

    # Step 12: remove technical/source columns from the final output.
    return drop_output_columns(deduplicated_df)
