from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.db import connection

TRANSIT_SCHEMA = "transit"
DASHBOARD_TABLE = "transit_for_dashboard_on_ministry_portal"
DASHBOARD_DATE_COLUMN = "Çıxış tarixi"


def quote_name(name: str) -> str:
    return connection.ops.quote_name(name)


def dashboard_qualified_table() -> str:
    return f"{quote_name(TRANSIT_SCHEMA)}.{quote_name(DASHBOARD_TABLE)}"


@dataclass(frozen=True)
class TransitDataPeriods:
    """Comparison windows derived from the latest exit date in dashboard data."""

    reference_year: int
    reference_month: int
    annual_year_previous: int
    annual_year_current: int
    annual_previous_start: date
    annual_previous_end: date
    annual_current_start: date
    annual_current_end: date
    partial_year_previous: int
    partial_year_current: int
    partial_previous_start: date
    partial_previous_end: date
    partial_current_start: date
    partial_current_end: date

    @property
    def partial_label(self) -> str:
        return f"{self.partial_year_current}-cı ilin ilk {self.reference_month} ayında"

    @property
    def partial_period_label(self) -> str:
        return f"{self.partial_year_current} Yan-{self.reference_month:02d}"

    @property
    def partial_previous_period_label(self) -> str:
        return f"{self.partial_year_previous} Yan-{self.reference_month:02d}"

    @property
    def annual_previous_label(self) -> str:
        return str(self.annual_year_previous)

    @property
    def annual_current_label(self) -> str:
        return str(self.annual_year_current)

    @property
    def partial_previous_header(self) -> str:
        return f"{self.partial_year_previous}*"

    @property
    def partial_current_header(self) -> str:
        return f"{self.partial_year_current}*"


def month_range_end(year: int, month: int) -> date:
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def compute_transit_data_periods(reference_year: int, reference_month: int) -> TransitDataPeriods:
    if reference_month < 1 or reference_month > 12:
        raise ValueError(f"reference_month must be 1-12, got {reference_month}")

    annual_year_current = reference_year - 1
    annual_year_previous = reference_year - 2
    partial_year_current = reference_year
    partial_year_previous = reference_year - 1
    partial_end = month_range_end(reference_year, reference_month)
    partial_previous_end = month_range_end(partial_year_previous, reference_month)

    return TransitDataPeriods(
        reference_year=reference_year,
        reference_month=reference_month,
        annual_year_previous=annual_year_previous,
        annual_year_current=annual_year_current,
        annual_previous_start=date(annual_year_previous, 1, 1),
        annual_previous_end=date(annual_year_previous + 1, 1, 1),
        annual_current_start=date(annual_year_current, 1, 1),
        annual_current_end=date(annual_year_current + 1, 1, 1),
        partial_year_previous=partial_year_previous,
        partial_year_current=partial_year_current,
        partial_previous_start=date(partial_year_previous, 1, 1),
        partial_previous_end=partial_previous_end,
        partial_current_start=date(partial_year_current, 1, 1),
        partial_current_end=partial_end,
    )


def load_transit_data_periods() -> TransitDataPeriods | None:
    quoted_date_column = quote_name(DASHBOARD_DATE_COLUMN)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT MAX({quoted_date_column}::date)
            FROM {dashboard_qualified_table()}
            """
        )
        max_date = cursor.fetchone()[0]

    if max_date is None:
        return None

    return compute_transit_data_periods(max_date.year, max_date.month)


def format_dynamics_report_number(periods: TransitDataPeriods) -> str:
    return f"TR-001-{periods.reference_year}/{periods.reference_month:02d}-Dinamika"
