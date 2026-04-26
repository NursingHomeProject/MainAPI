from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from uuid import UUID

from app.core.config import settings
from app.modules.calculation.core.fixed_usage import (
    parse_specific_times_safe,
    resolve_prescription_effective_window_start,
)
from app.modules.calculation.schemas import CalculationAdministrationDayStatus


class DoseScheduleState(str, Enum):
    NOT_DUE_YET = "not_due_yet"
    DUE_NOW = "due_now"
    OVERDUE = "overdue"
    COMPLETED = "completed"


@dataclass(frozen=True)
class DoseTimingPolicy:
    tolerance_minutes: int

    @property
    def tolerance_delta(self) -> timedelta:
        return timedelta(minutes=self.tolerance_minutes)


@dataclass(frozen=True)
class DoseAdministrationRecord:
    occurred_at: datetime
    quantity: Decimal
    prescription_id: UUID | None = None


@dataclass(frozen=True)
class DoseOccurrenceEvaluation:
    scheduled_at: datetime
    tolerated_until: datetime
    dose_amount: Decimal
    state: DoseScheduleState
    prescription_id: UUID | None = None
    matched_occurred_at: datetime | None = None


@dataclass(frozen=True)
class DoseOccurrenceSummary:
    expected_chargeable_quantity: Decimal
    completed_quantity: Decimal


@dataclass(frozen=True)
class DoseDayStatusSummary:
    status: CalculationAdministrationDayStatus
    reason: str


def resolve_dose_timing_policy(
    tolerance_minutes: int | None = None,
) -> DoseTimingPolicy:
    resolved_tolerance_minutes = (
        settings.dose_administration_tolerance_minutes
        if tolerance_minutes is None
        else tolerance_minutes
    )

    if resolved_tolerance_minutes < 0:
        raise ValueError("Dose administration tolerance cannot be negative.")

    return DoseTimingPolicy(tolerance_minutes=resolved_tolerance_minutes)


def classify_scheduled_dose_state(
    *,
    scheduled_at: datetime,
    reference_datetime: datetime,
    has_matching_administration: bool,
    timing_policy: DoseTimingPolicy | None = None,
) -> DoseScheduleState:
    """
    Operational rule for scheduled doses in the MVP:

    - Future doses on the same day are not charged yet.
    - Once the scheduled time arrives, the dose is considered due.
    - The dose remains in ``due_now`` while it is inside the tolerated delay.
    - After the tolerance window expires without a matching administration,
      the dose becomes ``overdue``.
    - A matching administration always wins and marks the occurrence as
      ``completed``.

    The tolerance is intentionally global for the MVP. This keeps the rule
    easy to reason about and avoids multiplying operational settings per
    prescription before the team has enough real-world usage to justify it.

    This helper intentionally does not decide *how* an administration is
    matched to a dose occurrence yet. That part is the next integration phase.
    Here we formalize only the time-based interpretation rule.
    """

    policy = timing_policy or resolve_dose_timing_policy()

    if has_matching_administration:
        return DoseScheduleState.COMPLETED

    if reference_datetime < scheduled_at:
        return DoseScheduleState.NOT_DUE_YET

    tolerated_until = scheduled_at + policy.tolerance_delta
    if reference_datetime <= tolerated_until:
        return DoseScheduleState.DUE_NOW

    return DoseScheduleState.OVERDUE


def build_fixed_dose_occurrences(
    prescriptions,
    *,
    administration_records: list[DoseAdministrationRecord],
    reference_datetime: datetime,
    timing_policy: DoseTimingPolicy | None = None,
) -> list[DoseOccurrenceEvaluation]:
    policy = timing_policy or resolve_dose_timing_policy()
    raw_occurrences = _build_raw_dose_occurrences(
        prescriptions,
        reference_datetime=reference_datetime,
        timing_policy=policy,
    )
    administration_allocations = _build_administration_allocations(
        administration_records,
        reference_datetime=reference_datetime,
    )

    _assign_administrations_to_occurrences(
        raw_occurrences,
        administration_allocations=administration_allocations,
        reference_datetime=reference_datetime,
        timing_policy=policy,
    )

    return [
        DoseOccurrenceEvaluation(
            scheduled_at=raw_occurrence.scheduled_at,
            tolerated_until=raw_occurrence.scheduled_at + policy.tolerance_delta,
            dose_amount=raw_occurrence.dose_amount,
            state=classify_scheduled_dose_state(
                scheduled_at=raw_occurrence.scheduled_at,
                reference_datetime=reference_datetime,
                has_matching_administration=raw_occurrence.matched_occurred_at
                is not None,
                timing_policy=policy,
            ),
            prescription_id=raw_occurrence.prescription_id,
            matched_occurred_at=raw_occurrence.matched_occurred_at,
        )
        for raw_occurrence in raw_occurrences
    ]


def summarize_dose_occurrences(
    occurrences: list[DoseOccurrenceEvaluation],
) -> DoseOccurrenceSummary:
    expected_chargeable_quantity = Decimal("0")
    completed_quantity = Decimal("0")

    for occurrence in occurrences:
        if occurrence.state in {
            DoseScheduleState.COMPLETED,
            DoseScheduleState.OVERDUE,
        }:
            expected_chargeable_quantity += occurrence.dose_amount
        if occurrence.state == DoseScheduleState.COMPLETED:
            completed_quantity += occurrence.dose_amount

    return DoseOccurrenceSummary(
        expected_chargeable_quantity=expected_chargeable_quantity,
        completed_quantity=completed_quantity,
    )


def classify_dose_day_status(
    occurrences: list[DoseOccurrenceEvaluation],
) -> DoseDayStatusSummary:
    """
    Day-level priority is intentionally linear:

    1. missed_dose: at least one overdue occurrence
    2. due_now: no overdue occurrence, but at least one dose is currently due
    3. partially_completed_day: at least one dose completed and the remaining ones are future
    4. completed: every scheduled dose of the day is completed
    5. not_due_yet: no dose became due yet
    """

    if not occurrences:
        return DoseDayStatusSummary(
            status=CalculationAdministrationDayStatus.NOT_DUE_YET,
            reason="Nao ha mais doses programadas para hoje a partir do momento de ativacao da prescricao.",
        )

    states = {occurrence.state for occurrence in occurrences}
    if DoseScheduleState.OVERDUE in states:
        return DoseDayStatusSummary(
            status=CalculationAdministrationDayStatus.MISSED_DOSE,
            reason="Existe dose atrasada sem registro de administracao apos a tolerancia configurada.",
        )

    if DoseScheduleState.DUE_NOW in states:
        return DoseDayStatusSummary(
            status=CalculationAdministrationDayStatus.DUE_NOW,
            reason="Existe dose dentro da janela de administracao e ainda dentro da tolerancia.",
        )

    if all(state == DoseScheduleState.COMPLETED for state in states):
        return DoseDayStatusSummary(
            status=CalculationAdministrationDayStatus.COMPLETED,
            reason="Todas as doses previstas do dia ja foram registradas.",
        )

    if (
        DoseScheduleState.COMPLETED in states
        and states.issubset(
            {DoseScheduleState.COMPLETED, DoseScheduleState.NOT_DUE_YET}
        )
    ):
        return DoseDayStatusSummary(
            status=CalculationAdministrationDayStatus.PARTIALLY_COMPLETED_DAY,
            reason="Parte das doses do dia ja foi concluida e ainda ha dose futura pendente.",
        )

    return DoseDayStatusSummary(
        status=CalculationAdministrationDayStatus.NOT_DUE_YET,
        reason="Ainda nao ha dose vencida ou em janela de administracao neste momento.",
    )


@dataclass
class _RawDoseOccurrence:
    scheduled_at: datetime
    dose_amount: Decimal
    prescription_id: UUID | None
    matched_occurred_at: datetime | None = None


@dataclass
class _AdministrationAllocation:
    occurred_at: datetime
    remaining_quantity: Decimal
    prescription_id: UUID | None


def _build_raw_dose_occurrences(
    prescriptions,
    *,
    reference_datetime: datetime,
    timing_policy: DoseTimingPolicy,
) -> list[_RawDoseOccurrence]:
    reference_date = reference_datetime.date()
    raw_occurrences: list[_RawDoseOccurrence] = []

    for prescription in prescriptions:
        start_date = getattr(prescription, "start_date", None)
        if start_date is None or start_date > reference_date:
            continue

        end_date = getattr(prescription, "end_date", None)
        if end_date is not None and end_date < reference_date:
            continue

        specific_times = parse_specific_times_safe(
            getattr(prescription, "specific_times", None)
        )
        if not specific_times:
            continue

        prescription_id = getattr(prescription, "id", None)
        dose_amount = getattr(prescription, "dose_amount", Decimal("0"))
        effective_window_start = resolve_prescription_effective_window_start(
            prescription,
            reference_datetime=reference_datetime,
        )
        for scheduled_time in specific_times:
            scheduled_at = datetime.combine(
                reference_date,
                scheduled_time,
            ).replace(tzinfo=reference_datetime.tzinfo)
            if (
                effective_window_start is not None
                and scheduled_at < effective_window_start
            ):
                continue
            raw_occurrences.append(
                _RawDoseOccurrence(
                    scheduled_at=scheduled_at,
                    dose_amount=dose_amount,
                    prescription_id=prescription_id,
                )
            )

    return sorted(raw_occurrences, key=lambda occurrence: occurrence.scheduled_at)


def _build_administration_allocations(
    administration_records: list[DoseAdministrationRecord],
    *,
    reference_datetime: datetime,
) -> list[_AdministrationAllocation]:
    allocations: list[_AdministrationAllocation] = []
    for record in administration_records:
        if record.occurred_at > reference_datetime:
            continue
        allocations.append(
            _AdministrationAllocation(
                occurred_at=record.occurred_at,
                remaining_quantity=record.quantity,
                prescription_id=record.prescription_id,
            )
        )
    return sorted(allocations, key=lambda allocation: allocation.occurred_at)


def _assign_administrations_to_occurrences(
    raw_occurrences: list[_RawDoseOccurrence],
    *,
    administration_allocations: list[_AdministrationAllocation],
    reference_datetime: datetime,
    timing_policy: DoseTimingPolicy,
) -> None:
    for allocation in administration_allocations:
        while True:
            best_occurrence = _find_best_matching_occurrence(
                raw_occurrences,
                allocation=allocation,
                reference_datetime=reference_datetime,
                timing_policy=timing_policy,
            )
            if best_occurrence is None:
                break

            allocation.remaining_quantity -= best_occurrence.dose_amount
            best_occurrence.matched_occurred_at = allocation.occurred_at


def _find_best_matching_occurrence(
    raw_occurrences: list[_RawDoseOccurrence],
    *,
    allocation: _AdministrationAllocation,
    reference_datetime: datetime,
    timing_policy: DoseTimingPolicy,
) -> _RawDoseOccurrence | None:
    candidates: list[_RawDoseOccurrence] = []

    for occurrence in raw_occurrences:
        if occurrence.matched_occurred_at is not None:
            continue

        if allocation.remaining_quantity < occurrence.dose_amount:
            continue

        if (
            allocation.prescription_id is not None
            and occurrence.prescription_id is not None
            and allocation.prescription_id != occurrence.prescription_id
        ):
            continue

        if allocation.occurred_at > reference_datetime:
            continue

        lower_bound = occurrence.scheduled_at - timing_policy.tolerance_delta
        if allocation.occurred_at < lower_bound:
            continue

        candidates.append(occurrence)

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda occurrence: (
            abs((allocation.occurred_at - occurrence.scheduled_at).total_seconds()),
            occurrence.scheduled_at,
        ),
    )
