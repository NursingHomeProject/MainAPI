from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.modules.calculation.core.basic import build_basic_calculation_payload
from app.modules.calculation.schemas import (
    CalculationDivergenceStatus,
    CalculationOperationalStatus,
)
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)


class CalculationEngineTests(unittest.TestCase):
    def _build_payload(
        self,
        *,
        daily_consumption: str,
        current_stock: str,
        expected_consumption_until_now: str | None,
        actual_consumption_until_now: str | None,
    ):
        return build_basic_calculation_payload(
            reference_date=date(2026, 4, 8),
            patient_id=uuid4(),
            patient_name="Maria da Conceicao",
            item_id=uuid4(),
            item_name="Dipirona 500mg",
            unit_symbol="comprimido",
            usage_mode=PrescriptionUsageMode.FIXED,
            comparison_window=PrescriptionComparisonWindow.DAILY_TOTAL,
            daily_consumption=Decimal(daily_consumption),
            current_stock=Decimal(current_stock),
            expected_consumption_until_now=(
                Decimal(expected_consumption_until_now)
                if expected_consumption_until_now is not None
                else None
            ),
            actual_consumption_until_now=(
                Decimal(actual_consumption_until_now)
                if actual_consumption_until_now is not None
                else None
            ),
        )

    def test_returns_ok_for_normal_balance(self):
        payload = self._build_payload(
            daily_consumption="3",
            current_stock="30",
            expected_consumption_until_now="24",
            actual_consumption_until_now="24",
        )

        self.assertEqual(payload.status, CalculationOperationalStatus.OK)
        self.assertEqual(payload.divergence_status, CalculationDivergenceStatus.COHERENT)
        self.assertEqual(payload.days_remaining, Decimal("10.00"))
        self.assertFalse(payload.should_alert)

    def test_returns_critical_stock_when_days_remaining_is_three_or_less(self):
        payload = self._build_payload(
            daily_consumption="1",
            current_stock="2",
            expected_consumption_until_now="8",
            actual_consumption_until_now="8",
        )

        self.assertEqual(payload.status, CalculationOperationalStatus.CRITICAL_STOCK)
        self.assertEqual(payload.days_remaining, Decimal("2.00"))
        self.assertTrue(payload.should_alert)

    def test_returns_consumption_above_expected(self):
        payload = self._build_payload(
            daily_consumption="3",
            current_stock="40",
            expected_consumption_until_now="24",
            actual_consumption_until_now="30",
        )

        self.assertEqual(
            payload.status,
            CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED,
        )
        self.assertEqual(payload.divergence, Decimal("6.000"))
        self.assertEqual(payload.divergence_status, CalculationDivergenceStatus.ABOVE_EXPECTED)
        self.assertTrue(payload.should_alert)

    def test_returns_consumption_below_expected(self):
        payload = self._build_payload(
            daily_consumption="3",
            current_stock="40",
            expected_consumption_until_now="24",
            actual_consumption_until_now="12",
        )

        self.assertEqual(
            payload.status,
            CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
        )
        self.assertEqual(payload.divergence, Decimal("-12.000"))
        self.assertEqual(payload.divergence_status, CalculationDivergenceStatus.BELOW_EXPECTED)
        self.assertTrue(payload.should_alert)

    def test_returns_invalid_prescription_without_active_prescription(self):
        payload = self._build_payload(
            daily_consumption="0",
            current_stock="10",
            expected_consumption_until_now=None,
            actual_consumption_until_now=None,
        )

        self.assertEqual(
            payload.status,
            CalculationOperationalStatus.INVALID_PRESCRIPTION,
        )
        self.assertIsNone(payload.days_remaining)
        self.assertFalse(payload.is_valid)
        self.assertTrue(payload.should_alert)

    def test_returns_critical_stock_for_zero_stock(self):
        payload = self._build_payload(
            daily_consumption="3",
            current_stock="0",
            expected_consumption_until_now="24",
            actual_consumption_until_now="24",
        )

        self.assertEqual(payload.status, CalculationOperationalStatus.CRITICAL_STOCK)
        self.assertEqual(payload.days_remaining, Decimal("0.00"))
        self.assertTrue(payload.should_alert)

    def test_returns_inconsistent_data_for_negative_stock(self):
        payload = self._build_payload(
            daily_consumption="3",
            current_stock="-1",
            expected_consumption_until_now="24",
            actual_consumption_until_now="24",
        )

        self.assertEqual(payload.status, CalculationOperationalStatus.INCONSISTENT_DATA)
        self.assertFalse(payload.is_valid)
        self.assertTrue(payload.should_alert)


if __name__ == "__main__":
    unittest.main()
