from datetime import date

from django.test import TestCase

from apps.dashboard.transit_periods import compute_transit_data_periods


class TransitDataPeriodsTests(TestCase):
    def test_compute_periods_from_latest_data_may_2026(self):
        periods = compute_transit_data_periods(2026, 5)

        self.assertEqual(periods.reference_year, 2026)
        self.assertEqual(periods.reference_month, 5)
        self.assertEqual(periods.annual_year_current, 2025)
        self.assertEqual(periods.annual_year_previous, 2024)
        self.assertEqual(periods.partial_year_current, 2026)
        self.assertEqual(periods.partial_year_previous, 2025)

        self.assertEqual(periods.annual_current_start, date(2025, 1, 1))
        self.assertEqual(periods.annual_current_end, date(2026, 1, 1))
        self.assertEqual(periods.annual_previous_start, date(2024, 1, 1))
        self.assertEqual(periods.annual_previous_end, date(2025, 1, 1))

        self.assertEqual(periods.partial_current_start, date(2026, 1, 1))
        self.assertEqual(periods.partial_current_end, date(2026, 6, 1))
        self.assertEqual(periods.partial_previous_start, date(2025, 1, 1))
        self.assertEqual(periods.partial_previous_end, date(2025, 6, 1))

        self.assertEqual(periods.partial_label, "2026-cı ilin ilk 5 ayında")
        self.assertEqual(periods.partial_period_label, "2026 Yan-05")

    def test_compute_periods_handles_december(self):
        periods = compute_transit_data_periods(2025, 12)

        self.assertEqual(periods.partial_current_end, date(2026, 1, 1))
        self.assertEqual(periods.partial_previous_end, date(2025, 1, 1))
