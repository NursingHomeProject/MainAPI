from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from zoneinfo import ZoneInfo

from app.modules.calculation.core.dose_schedule import (
    classify_dose_day_status,
    DoseAdministrationRecord,
    DoseOccurrenceEvaluation,
    DoseTimingPolicy,
    DoseScheduleState,
    build_fixed_dose_occurrences,
    classify_scheduled_dose_state,
    resolve_dose_timing_policy,
)
from app.modules.calculation.schemas import CalculationAdministrationDayStatus


class DoseScheduleRuleTests(TestCase):
    timezone = ZoneInfo("America/Sao_Paulo")

    def test_morning_rule_only_charges_the_dose_that_already_arrived(self) -> None:
        timing_policy = resolve_dose_timing_policy(tolerance_minutes=60)
        reference_datetime = datetime(2026, 4, 12, 10, 0, tzinfo=self.timezone)

        morning_dose_state = classify_scheduled_dose_state(
            scheduled_at=datetime(2026, 4, 12, 8, 0, tzinfo=self.timezone),
            reference_datetime=reference_datetime,
            has_matching_administration=False,
            timing_policy=timing_policy,
        )
        night_dose_state = classify_scheduled_dose_state(
            scheduled_at=datetime(2026, 4, 12, 20, 0, tzinfo=self.timezone),
            reference_datetime=reference_datetime,
            has_matching_administration=False,
            timing_policy=timing_policy,
        )

        self.assertEqual(morning_dose_state, DoseScheduleState.OVERDUE)
        self.assertEqual(night_dose_state, DoseScheduleState.NOT_DUE_YET)

    def test_afternoon_rule_keeps_recent_dose_due_inside_tolerance(self) -> None:
        timing_policy = resolve_dose_timing_policy(tolerance_minutes=60)
        reference_datetime = datetime(2026, 4, 12, 14, 30, tzinfo=self.timezone)

        dose_state = classify_scheduled_dose_state(
            scheduled_at=datetime(2026, 4, 12, 14, 0, tzinfo=self.timezone),
            reference_datetime=reference_datetime,
            has_matching_administration=False,
            timing_policy=timing_policy,
        )

        self.assertEqual(dose_state, DoseScheduleState.DUE_NOW)

    def test_night_rule_marks_dose_as_completed_when_registered(self) -> None:
        timing_policy = resolve_dose_timing_policy(tolerance_minutes=60)
        reference_datetime = datetime(2026, 4, 12, 22, 0, tzinfo=self.timezone)

        dose_state = classify_scheduled_dose_state(
            scheduled_at=datetime(2026, 4, 12, 20, 0, tzinfo=self.timezone),
            reference_datetime=reference_datetime,
            has_matching_administration=True,
            timing_policy=timing_policy,
        )

        self.assertEqual(dose_state, DoseScheduleState.COMPLETED)

    def test_zero_tolerance_marks_the_dose_overdue_as_soon_as_the_time_passes(self) -> None:
        timing_policy = resolve_dose_timing_policy(tolerance_minutes=0)
        reference_datetime = datetime(2026, 4, 12, 8, 1, tzinfo=self.timezone)

        dose_state = classify_scheduled_dose_state(
            scheduled_at=datetime(2026, 4, 12, 8, 0, tzinfo=self.timezone),
            reference_datetime=reference_datetime,
            has_matching_administration=False,
            timing_policy=timing_policy,
        )

        self.assertEqual(dose_state, DoseScheduleState.OVERDUE)

    def test_negative_tolerance_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_dose_timing_policy(tolerance_minutes=-1)

    def test_default_tolerance_policy_is_global_for_the_mvp(self) -> None:
        timing_policy = resolve_dose_timing_policy()

        self.assertEqual(timing_policy.tolerance_minutes, 30)

    def test_evening_administration_matches_the_evening_dose_not_the_morning_one(self) -> None:
        prescription = type(
            "PrescriptionStub",
            (),
            {
                "id": "prescription-1",
                "dose_amount": Decimal("1"),
                "frequency_per_day": 2,
                "specific_times": ["08:00", "20:00"],
                "start_date": datetime(2026, 4, 12, 0, 0, tzinfo=self.timezone).date(),
                "end_date": None,
            },
        )()

        occurrences = build_fixed_dose_occurrences(
            [prescription],
            administration_records=[
                DoseAdministrationRecord(
                    occurred_at=datetime(2026, 4, 12, 19, 50, tzinfo=self.timezone),
                    quantity=Decimal("1"),
                    prescription_id="prescription-1",
                )
            ],
            reference_datetime=datetime(2026, 4, 12, 22, 0, tzinfo=self.timezone),
        )

        self.assertEqual(
            [occurrence.state for occurrence in occurrences],
            [DoseScheduleState.OVERDUE, DoseScheduleState.COMPLETED],
        )

    def test_mvp_tolerance_example_uses_not_due_yet_due_now_and_overdue(self) -> None:
        timing_policy = resolve_dose_timing_policy(tolerance_minutes=30)
        scheduled_at = datetime(2026, 4, 12, 20, 0, tzinfo=self.timezone)

        self.assertEqual(
            classify_scheduled_dose_state(
                scheduled_at=scheduled_at,
                reference_datetime=datetime(2026, 4, 12, 19, 50, tzinfo=self.timezone),
                has_matching_administration=False,
                timing_policy=timing_policy,
            ),
            DoseScheduleState.NOT_DUE_YET,
        )
        self.assertEqual(
            classify_scheduled_dose_state(
                scheduled_at=scheduled_at,
                reference_datetime=datetime(2026, 4, 12, 20, 10, tzinfo=self.timezone),
                has_matching_administration=False,
                timing_policy=timing_policy,
            ),
            DoseScheduleState.DUE_NOW,
        )
        self.assertEqual(
            classify_scheduled_dose_state(
                scheduled_at=scheduled_at,
                reference_datetime=datetime(2026, 4, 12, 20, 35, tzinfo=self.timezone),
                has_matching_administration=False,
                timing_policy=timing_policy,
            ),
            DoseScheduleState.OVERDUE,
        )

    def test_day_status_marks_partially_completed_day(self) -> None:
        day_status = classify_dose_day_status(
            [
                DoseOccurrenceEvaluation(
                    scheduled_at=datetime(2026, 4, 12, 8, 0, tzinfo=self.timezone),
                    tolerated_until=datetime(2026, 4, 12, 8, 30, tzinfo=self.timezone),
                    dose_amount=Decimal("1"),
                    state=DoseScheduleState.COMPLETED,
                ),
                DoseOccurrenceEvaluation(
                    scheduled_at=datetime(2026, 4, 12, 20, 0, tzinfo=self.timezone),
                    tolerated_until=datetime(2026, 4, 12, 20, 30, tzinfo=self.timezone),
                    dose_amount=Decimal("1"),
                    state=DoseScheduleState.NOT_DUE_YET,
                ),
            ]
        )

        self.assertEqual(
            day_status.status,
            CalculationAdministrationDayStatus.PARTIALLY_COMPLETED_DAY,
        )

    def test_day_status_without_remaining_occurrences_after_activation_is_not_due_yet(self) -> None:
        day_status = classify_dose_day_status([])

        self.assertEqual(
            day_status.status,
            CalculationAdministrationDayStatus.NOT_DUE_YET,
        )

    def test_day_status_prioritizes_missed_dose_over_other_states(self) -> None:
        day_status = classify_dose_day_status(
            [
                DoseOccurrenceEvaluation(
                    scheduled_at=datetime(2026, 4, 12, 8, 0, tzinfo=self.timezone),
                    tolerated_until=datetime(2026, 4, 12, 8, 30, tzinfo=self.timezone),
                    dose_amount=Decimal("1"),
                    state=DoseScheduleState.COMPLETED,
                ),
                DoseOccurrenceEvaluation(
                    scheduled_at=datetime(2026, 4, 12, 12, 0, tzinfo=self.timezone),
                    tolerated_until=datetime(2026, 4, 12, 12, 30, tzinfo=self.timezone),
                    dose_amount=Decimal("1"),
                    state=DoseScheduleState.OVERDUE,
                ),
                DoseOccurrenceEvaluation(
                    scheduled_at=datetime(2026, 4, 12, 20, 0, tzinfo=self.timezone),
                    tolerated_until=datetime(2026, 4, 12, 20, 30, tzinfo=self.timezone),
                    dose_amount=Decimal("1"),
                    state=DoseScheduleState.NOT_DUE_YET,
                ),
            ]
        )

        self.assertEqual(
            day_status.status,
            CalculationAdministrationDayStatus.MISSED_DOSE,
        )

    def test_late_registered_dose_is_classified_as_completed_after_the_record_exists(self) -> None:
        prescription = type(
            "PrescriptionStub",
            (),
            {
                "id": "prescription-1",
                "dose_amount": Decimal("1"),
                "frequency_per_day": 1,
                "specific_times": ["08:00"],
                "start_date": datetime(2026, 4, 12, 0, 0, tzinfo=self.timezone).date(),
                "end_date": None,
            },
        )()

        occurrences = build_fixed_dose_occurrences(
            [prescription],
            administration_records=[
                DoseAdministrationRecord(
                    occurred_at=datetime(2026, 4, 12, 9, 45, tzinfo=self.timezone),
                    quantity=Decimal("1"),
                    prescription_id="prescription-1",
                )
            ],
            reference_datetime=datetime(2026, 4, 12, 10, 0, tzinfo=self.timezone),
        )

        self.assertEqual(len(occurrences), 1)
        self.assertEqual(occurrences[0].state, DoseScheduleState.COMPLETED)
        self.assertEqual(
            occurrences[0].matched_occurred_at,
            datetime(2026, 4, 12, 9, 45, tzinfo=self.timezone),
        )
