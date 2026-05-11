from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.modules.calculation.core.dose_schedule import (
    DoseAdministrationRecord,
    DoseScheduleState,
    build_fixed_dose_occurrences,
    summarize_dose_occurrences,
)
from app.modules.calculation.core.fixed_usage import (
    calculate_expected_fixed_consumption_until_now,
)
from app.modules.calculation.core.usage_modes import resolve_usage_mode_plan
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)


class CalculationFixedScheduleTests(unittest.TestCase):
    def _build_prescription(
        self,
        *,
        dose_amount: str = "1",
        frequency_per_day: int = 2,
        specific_times: list[str] | None = None,
        usage_mode: PrescriptionUsageMode = PrescriptionUsageMode.FIXED,
        comparison_window: PrescriptionComparisonWindow = PrescriptionComparisonWindow.DAILY_TOTAL,
        start_date_value: date = date(2026, 4, 10),
        created_at_value: datetime | None = None,
    ):
        return SimpleNamespace(
            dose_amount=Decimal(dose_amount),
            frequency_per_day=frequency_per_day,
            specific_times=specific_times,
            usage_mode=usage_mode,
            comparison_window=comparison_window,
            min_expected_per_day=None,
            max_expected_per_day=None,
            start_date=start_date_value,
            end_date=None,
            created_at=created_at_value,
        )

    def test_morning_only_charges_due_doses(self):
        prescription = self._build_prescription(
            specific_times=["08:00", "20:00"],
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )

        self.assertTrue(plan.use_dose_occurrences)
        self.assertIsNone(plan.exact_expected_consumption_until_now)
        self.assertEqual(
            plan.comparison_window,
            PrescriptionComparisonWindow.SCHEDULED_TIMES,
        )

    def test_afternoon_counts_only_completed_scheduled_times(self):
        prescription = self._build_prescription(
            frequency_per_day=3,
            specific_times=["08:00", "12:00", "20:00"],
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 15, 0),
        )

        self.assertTrue(plan.use_dose_occurrences)
        self.assertIsNone(plan.exact_expected_consumption_until_now)

    def test_night_counts_all_scheduled_doses_of_the_day(self):
        prescription = self._build_prescription(
            specific_times=["08:00", "20:00"],
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 22, 0),
        )

        self.assertTrue(plan.use_dose_occurrences)
        self.assertIsNone(plan.exact_expected_consumption_until_now)

    def test_invalid_or_missing_times_fall_back_to_full_daily_total(self):
        prescription = self._build_prescription(
            specific_times=["08:00", "horario-invalido"],
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )

        self.assertEqual(
            plan.exact_expected_consumption_until_now,
            Decimal("0.8333333333333334"),
        )
        self.assertEqual(
            plan.comparison_window,
            PrescriptionComparisonWindow.DAILY_TOTAL,
        )

    def test_scheduled_fixed_window_does_not_accumulate_previous_days(self):
        prescription = self._build_prescription(
            specific_times=["08:00", "20:00"],
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
            start_date_value=date(2026, 4, 1),
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )

        self.assertTrue(plan.use_dose_occurrences)
        self.assertIsNone(plan.exact_expected_consumption_until_now)

    def test_fixed_helper_returns_none_for_non_fixed_usage(self):
        prescription = self._build_prescription(
            specific_times=["08:00", "20:00"],
            usage_mode=PrescriptionUsageMode.VARIABLE,
        )

        expected = calculate_expected_fixed_consumption_until_now(
            prescription,
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )

        self.assertIsNone(expected)

    def test_build_fixed_dose_occurrences_classifies_multiple_doses_of_the_day(self):
        prescription = self._build_prescription(
            specific_times=["08:00", "12:00", "20:00"],
            frequency_per_day=3,
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
        )
        prescription.id = "prescription-1"

        occurrences = build_fixed_dose_occurrences(
            [prescription],
            administration_records=[
                DoseAdministrationRecord(
                    occurred_at=datetime(2026, 4, 10, 8, 5),
                    quantity=Decimal("1"),
                    prescription_id="prescription-1",
                )
            ],
            reference_datetime=datetime(2026, 4, 10, 15, 0),
        )

        self.assertEqual(
            [occurrence.state for occurrence in occurrences],
            [
                DoseScheduleState.COMPLETED,
                DoseScheduleState.OVERDUE,
                DoseScheduleState.NOT_DUE_YET,
            ],
        )

        summary = summarize_dose_occurrences(occurrences)
        self.assertEqual(summary.completed_quantity, Decimal("1"))
        self.assertEqual(summary.expected_chargeable_quantity, Decimal("2"))

    def test_build_fixed_dose_occurrences_skips_times_before_same_day_creation(self):
        prescription = self._build_prescription(
            specific_times=["08:00", "20:00"],
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
            created_at_value=datetime(2026, 4, 10, 9, 30),
        )
        prescription.id = "prescription-2"

        occurrences = build_fixed_dose_occurrences(
            [prescription],
            administration_records=[],
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )

        self.assertEqual(len(occurrences), 1)
        self.assertEqual(
            occurrences[0].scheduled_at,
            datetime(2026, 4, 10, 20, 0),
        )
        self.assertEqual(occurrences[0].state, DoseScheduleState.NOT_DUE_YET)


if __name__ == "__main__":
    unittest.main()
