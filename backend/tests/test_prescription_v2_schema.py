from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from fastapi import HTTPException

from app.modules.prescriptions.models import (
    Prescription,
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)
from app.modules.prescriptions.schemas import PrescriptionCreate
from app.modules.prescriptions.services import validate_prescription_consistency


class PrescriptionV2SchemaTests(unittest.TestCase):
    def test_sqlalchemy_enum_columns_use_persisted_lowercase_values(self):
        usage_mode_type = Prescription.__table__.c.usage_mode.type
        comparison_window_type = Prescription.__table__.c.comparison_window.type

        self.assertEqual(usage_mode_type.enums, ["fixed", "variable", "on_demand"])
        self.assertEqual(
            comparison_window_type.enums,
            ["scheduled_times", "daily_total", "shift_window", "rolling_24h"],
        )
        self.assertEqual(
            usage_mode_type._object_lookup["fixed"],
            PrescriptionUsageMode.FIXED,
        )
        self.assertEqual(
            comparison_window_type._object_lookup["daily_total"],
            PrescriptionComparisonWindow.DAILY_TOTAL,
        )

    def test_prescription_create_defaults_to_fixed_daily_total(self):
        payload = PrescriptionCreate(
            patient_id="42caed51-6089-4908-8b59-7dcd4d718a27",
            item_id="722b0bc0-dc8f-436b-866e-44c064b42c2d",
            dose_amount=Decimal("1"),
            frequency_per_day=2,
            start_date=date(2026, 4, 10),
        )

        self.assertEqual(payload.usage_mode, PrescriptionUsageMode.FIXED)
        self.assertEqual(
            payload.comparison_window,
            PrescriptionComparisonWindow.DAILY_TOTAL,
        )
        self.assertIsNone(payload.min_expected_per_day)
        self.assertIsNone(payload.max_expected_per_day)

    def test_variable_prescription_accepts_expected_range(self):
        payload = PrescriptionCreate(
            patient_id="42caed51-6089-4908-8b59-7dcd4d718a27",
            item_id="722b0bc0-dc8f-436b-866e-44c064b42c2d",
            dose_amount=Decimal("1"),
            frequency_per_day=4,
            usage_mode=PrescriptionUsageMode.VARIABLE,
            comparison_window=PrescriptionComparisonWindow.ROLLING_24H,
            min_expected_per_day=Decimal("2"),
            max_expected_per_day=Decimal("6"),
            start_date=date(2026, 4, 10),
        )

        self.assertEqual(payload.min_expected_per_day, Decimal("2"))
        self.assertEqual(payload.max_expected_per_day, Decimal("6"))

    def test_fixed_prescription_rejects_expected_range(self):
        with self.assertRaisesRegex(
            ValueError,
            "Faixas esperadas por dia sao usadas apenas em prescricoes variaveis ou sob demanda.",
        ):
            PrescriptionCreate(
                patient_id="42caed51-6089-4908-8b59-7dcd4d718a27",
                item_id="722b0bc0-dc8f-436b-866e-44c064b42c2d",
                dose_amount=Decimal("1"),
                frequency_per_day=2,
                min_expected_per_day=Decimal("1"),
                max_expected_per_day=Decimal("3"),
                start_date=date(2026, 4, 10),
            )

    def test_service_validation_rejects_invalid_expected_range(self):
        with self.assertRaises(HTTPException):
            validate_prescription_consistency(
                frequency_per_day=3,
                specific_times=None,
                usage_mode=PrescriptionUsageMode.VARIABLE,
                comparison_window=PrescriptionComparisonWindow.ROLLING_24H,
                min_expected_per_day=Decimal("5"),
                max_expected_per_day=Decimal("2"),
                start_date=date(2026, 4, 10),
                end_date=None,
            )

    def test_fixed_scheduled_times_require_specific_times(self):
        with self.assertRaisesRegex(
            ValueError,
            "Prescricoes fixas com comparacao por horario exigem specific_times.",
        ):
            PrescriptionCreate(
                patient_id="42caed51-6089-4908-8b59-7dcd4d718a27",
                item_id="722b0bc0-dc8f-436b-866e-44c064b42c2d",
                dose_amount=Decimal("1"),
                frequency_per_day=2,
                usage_mode=PrescriptionUsageMode.FIXED,
                comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
                start_date=date(2026, 4, 10),
            )

    def test_variable_prescription_rejects_scheduled_times_window(self):
        with self.assertRaisesRegex(
            ValueError,
            "A janela scheduled_times e reservada para prescricoes fixas.",
        ):
            PrescriptionCreate(
                patient_id="42caed51-6089-4908-8b59-7dcd4d718a27",
                item_id="722b0bc0-dc8f-436b-866e-44c064b42c2d",
                dose_amount=Decimal("1"),
                frequency_per_day=4,
                usage_mode=PrescriptionUsageMode.VARIABLE,
                comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
                min_expected_per_day=Decimal("2"),
                max_expected_per_day=Decimal("6"),
                start_date=date(2026, 4, 10),
            )


if __name__ == "__main__":
    unittest.main()
