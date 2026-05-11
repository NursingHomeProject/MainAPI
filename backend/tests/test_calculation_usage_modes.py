from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.modules.calculation.core.basic import build_basic_calculation_payload
from app.modules.calculation.core.dose_schedule import (
    DoseAdministrationRecord,
    build_fixed_dose_occurrences,
    summarize_dose_occurrences,
)
from app.modules.calculation.core.usage_modes import (
    resolve_expected_consumption_for_plan,
    resolve_usage_mode_plan,
)
from app.modules.calculation.schemas import (
    CalculationDivergenceStatus,
    CalculationOperationalStatus,
)
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)


class CalculationUsageModeTests(unittest.TestCase):
    def _build_prescription(
        self,
        *,
        usage_mode: PrescriptionUsageMode,
        comparison_window: PrescriptionComparisonWindow,
        dose_amount: str = "1",
        frequency_per_day: int = 2,
        specific_times: list[str] | None = None,
        min_expected_per_day: str | None = None,
        max_expected_per_day: str | None = None,
        start_date_value: date = date(2026, 4, 10),
        created_at_value: datetime | None = None,
    ):
        return SimpleNamespace(
            dose_amount=Decimal(dose_amount),
            frequency_per_day=frequency_per_day,
            specific_times=specific_times,
            usage_mode=usage_mode,
            comparison_window=comparison_window,
            min_expected_per_day=(
                Decimal(min_expected_per_day)
                if min_expected_per_day is not None
                else None
            ),
            max_expected_per_day=(
                Decimal(max_expected_per_day)
                if max_expected_per_day is not None
                else None
            ),
            start_date=start_date_value,
            end_date=None,
            created_at=created_at_value,
        )

    def _build_payload_from_plan(
        self,
        plan,
        *,
        actual_consumption_until_now: Decimal | None,
        current_stock: str = "40",
    ):
        expected_consumption_until_now = resolve_expected_consumption_for_plan(
            plan,
            actual_consumption_until_now=actual_consumption_until_now,
        )
        return build_basic_calculation_payload(
            reference_date=date(2026, 4, 10),
            patient_id=uuid4(),
            patient_name="Paciente Teste",
            item_id=uuid4(),
            item_name="Dipirona 500mg",
            unit_symbol="comprimido",
            usage_mode=plan.usage_mode,
            comparison_window=plan.comparison_window,
            min_expected_per_day=plan.minimum_expected_per_day,
            max_expected_per_day=plan.maximum_expected_per_day,
            daily_consumption=plan.daily_consumption,
            current_stock=Decimal(current_stock),
            expected_consumption_until_now=expected_consumption_until_now,
            actual_consumption_until_now=actual_consumption_until_now,
            adherence_expected=plan.adherence_expected,
            invalid_reason_override=plan.invalid_reason,
        )

    def test_fixed_usage_plan_keeps_exact_schedule_based_expectation(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.FIXED,
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
            specific_times=["08:00", "20:00"],
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )

        self.assertEqual(plan.usage_mode, PrescriptionUsageMode.FIXED)
        self.assertTrue(plan.adherence_expected)
        self.assertTrue(plan.use_dose_occurrences)
        self.assertIsNone(plan.minimum_expected_per_day)
        self.assertIsNone(plan.maximum_expected_per_day)
        self.assertIsNone(plan.exact_expected_consumption_until_now)
        self.assertIsNone(plan.expected_min_until_now)
        self.assertIsNone(plan.expected_max_until_now)

    def test_fixed_scheduled_usage_does_not_alert_for_future_dose_of_same_day(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.FIXED,
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
            specific_times=["08:00", "20:00"],
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )

        occurrences = build_fixed_dose_occurrences(
            [prescription],
            administration_records=[
                DoseAdministrationRecord(
                    occurred_at=datetime(2026, 4, 10, 8, 5),
                    quantity=Decimal("1"),
                )
            ],
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )
        summary = summarize_dose_occurrences(occurrences)
        payload = build_basic_calculation_payload(
            reference_date=date(2026, 4, 10),
            patient_id=uuid4(),
            patient_name="Paciente Teste",
            item_id=uuid4(),
            item_name="Dipirona 500mg",
            unit_symbol="comprimido",
            usage_mode=plan.usage_mode,
            comparison_window=plan.comparison_window,
            min_expected_per_day=plan.minimum_expected_per_day,
            max_expected_per_day=plan.maximum_expected_per_day,
            daily_consumption=plan.daily_consumption,
            current_stock=Decimal("40"),
            expected_consumption_until_now=summary.expected_chargeable_quantity,
            actual_consumption_until_now=summary.completed_quantity,
            adherence_expected=plan.adherence_expected,
            invalid_reason_override=plan.invalid_reason,
        )

        self.assertEqual(payload.status, CalculationOperationalStatus.OK)
        self.assertEqual(payload.expected_consumption_until_now, Decimal("1.000"))
        self.assertEqual(payload.divergence, Decimal("0.000"))
        self.assertFalse(payload.should_alert)

    def test_variable_usage_plan_uses_range_and_window(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.VARIABLE,
            comparison_window=PrescriptionComparisonWindow.ROLLING_24H,
            min_expected_per_day="2",
            max_expected_per_day="5",
            frequency_per_day=1,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 15, 0),
        )

        self.assertEqual(plan.usage_mode, PrescriptionUsageMode.VARIABLE)
        self.assertTrue(plan.adherence_expected)
        self.assertIsNone(plan.exact_expected_consumption_until_now)
        self.assertEqual(plan.expected_min_until_now, Decimal("2"))
        self.assertEqual(plan.expected_max_until_now, Decimal("5"))
        self.assertEqual(plan.minimum_expected_per_day, Decimal("2"))
        self.assertEqual(plan.maximum_expected_per_day, Decimal("5"))
        self.assertEqual(
            plan.comparison_window,
            PrescriptionComparisonWindow.ROLLING_24H,
        )

        payload = self._build_payload_from_plan(
            plan,
            actual_consumption_until_now=Decimal("1"),
        )

        self.assertEqual(
            payload.status,
            CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
        )
        self.assertEqual(payload.divergence, Decimal("-1.000"))
        self.assertEqual(
            payload.divergence_status,
            CalculationDivergenceStatus.BELOW_EXPECTED,
        )
        self.assertEqual(
            payload.alert_reason,
            "Uso abaixo da faixa esperada na janela operacional.",
        )
        self.assertEqual(payload.min_expected_per_day, Decimal("2.000"))
        self.assertEqual(payload.max_expected_per_day, Decimal("5.000"))

    def test_variable_usage_plan_flags_consumption_above_range(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.VARIABLE,
            comparison_window=PrescriptionComparisonWindow.ROLLING_24H,
            min_expected_per_day="3",
            max_expected_per_day="5",
            frequency_per_day=1,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 15, 0),
        )

        payload = self._build_payload_from_plan(
            plan,
            actual_consumption_until_now=Decimal("6"),
        )

        self.assertEqual(
            payload.status,
            CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED,
        )
        self.assertEqual(payload.expected_consumption_until_now, Decimal("5.000"))
        self.assertEqual(payload.divergence, Decimal("1.000"))
        self.assertEqual(
            payload.divergence_status,
            CalculationDivergenceStatus.ABOVE_EXPECTED,
        )

    def test_variable_usage_plan_accepts_actual_within_range_without_alert(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.VARIABLE,
            comparison_window=PrescriptionComparisonWindow.ROLLING_24H,
            min_expected_per_day="3",
            max_expected_per_day="5",
            frequency_per_day=1,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 15, 0),
        )

        payload = self._build_payload_from_plan(
            plan,
            actual_consumption_until_now=Decimal("4"),
        )

        self.assertEqual(payload.status, CalculationOperationalStatus.OK)
        self.assertEqual(payload.expected_consumption_until_now, Decimal("4.000"))
        self.assertEqual(payload.divergence, Decimal("0.000"))
        self.assertEqual(
            payload.divergence_status,
            CalculationDivergenceStatus.COHERENT,
        )
        self.assertFalse(payload.should_alert)

    def test_variable_usage_plan_normalizes_scheduled_times_to_daily_total(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.VARIABLE,
            comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
            min_expected_per_day="3",
            max_expected_per_day="5",
            frequency_per_day=1,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 15, 0),
        )

        self.assertEqual(
            plan.comparison_window,
            PrescriptionComparisonWindow.DAILY_TOTAL,
        )

    def test_variable_usage_plan_supports_shift_window(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.VARIABLE,
            comparison_window=PrescriptionComparisonWindow.SHIFT_WINDOW,
            min_expected_per_day="3",
            max_expected_per_day="6",
            frequency_per_day=1,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 10, 0),
        )

        self.assertEqual(
            plan.comparison_window,
            PrescriptionComparisonWindow.SHIFT_WINDOW,
        )
        self.assertIsNotNone(plan.actual_window_start)
        self.assertEqual(plan.actual_window_start.hour, 8)
        self.assertLess(plan.expected_min_until_now, plan.expected_max_until_now)

    def test_on_demand_usage_plan_does_not_charge_adherence(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.ON_DEMAND,
            comparison_window=PrescriptionComparisonWindow.ROLLING_24H,
            max_expected_per_day="3",
            frequency_per_day=1,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 21, 0),
        )

        self.assertEqual(plan.usage_mode, PrescriptionUsageMode.ON_DEMAND)
        self.assertFalse(plan.adherence_expected)
        self.assertIsNone(plan.minimum_expected_per_day)
        self.assertEqual(plan.maximum_expected_per_day, Decimal("3"))
        self.assertIsNone(plan.exact_expected_consumption_until_now)
        self.assertIsNone(plan.expected_min_until_now)
        self.assertIsNone(plan.expected_max_until_now)

        payload = self._build_payload_from_plan(
            plan,
            actual_consumption_until_now=Decimal("0"),
        )

        self.assertEqual(payload.status, CalculationOperationalStatus.OK)
        self.assertIsNone(payload.expected_consumption_until_now)
        self.assertIsNone(payload.divergence)
        self.assertEqual(
            payload.divergence_status,
            CalculationDivergenceStatus.NOT_AVAILABLE,
        )
        self.assertFalse(payload.should_alert)
        self.assertIsNone(payload.min_expected_per_day)
        self.assertEqual(payload.max_expected_per_day, Decimal("3.000"))

    def test_on_demand_usage_plan_can_still_signal_low_stock(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.ON_DEMAND,
            comparison_window=PrescriptionComparisonWindow.ROLLING_24H,
            max_expected_per_day="3",
            frequency_per_day=1,
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 21, 0),
        )

        payload = self._build_payload_from_plan(
            plan,
            actual_consumption_until_now=Decimal("0"),
            current_stock="12",
        )

        self.assertEqual(payload.status, CalculationOperationalStatus.LOW_STOCK)
        self.assertEqual(payload.days_remaining, Decimal("4.00"))
        self.assertTrue(payload.should_alert)
        self.assertEqual(
            payload.alert_reason,
            "Saldo em faixa de atencao para uso sob demanda.",
        )

    def test_fixed_daily_total_same_day_creation_does_not_charge_retroactively(self):
        prescription = self._build_prescription(
            usage_mode=PrescriptionUsageMode.FIXED,
            comparison_window=PrescriptionComparisonWindow.DAILY_TOTAL,
            dose_amount="1",
            frequency_per_day=2,
            start_date_value=date(2026, 4, 10),
            created_at_value=datetime(2026, 4, 10, 15, 0),
        )

        plan = resolve_usage_mode_plan(
            [prescription],
            reference_datetime=datetime(2026, 4, 10, 15, 0),
        )

        self.assertEqual(
            plan.exact_expected_consumption_until_now,
            Decimal("0"),
        )
        self.assertEqual(plan.actual_window_start, datetime(2026, 4, 10, 15, 0))


if __name__ == "__main__":
    unittest.main()
