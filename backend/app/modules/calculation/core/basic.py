from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.calculation.core.calculation import quantize_quantity, quantize_ratio
from app.modules.calculation.core.status import classify_operational_status
from app.modules.calculation.schemas import (
    CalculationAdministrationDayStatus,
    CalculationDoseOccurrence,
    CalculationDoseScheduleSummary,
    CalculationDivergenceStatus,
    CalculationEnginePayload,
)
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)
COHERENCE_TOLERANCE = Decimal("0.001")


def build_basic_calculation_payload(
    *,
    reference_date: date,
    patient_id: UUID,
    patient_name: str,
    item_id: UUID,
    item_name: str,
    unit_symbol: str,
    usage_mode: PrescriptionUsageMode | None,
    comparison_window: PrescriptionComparisonWindow | None,
    min_expected_per_day: Decimal | None = None,
    max_expected_per_day: Decimal | None = None,
    daily_consumption: Decimal,
    current_stock: Decimal,
    expected_consumption_until_now: Decimal | None,
    actual_consumption_until_now: Decimal | None,
    dose_occurrences: list[CalculationDoseOccurrence] | None = None,
    dose_schedule: CalculationDoseScheduleSummary | None = None,
    administration_day_status: CalculationAdministrationDayStatus | None = None,
    administration_day_reason: str | None = None,
    adherence_expected: bool = True,
    invalid_reason_override: str | None = None,
) -> CalculationEnginePayload:
    normalized_daily_consumption = quantize_quantity(daily_consumption)
    normalized_min_expected_per_day = (
        quantize_quantity(min_expected_per_day)
        if min_expected_per_day is not None
        else None
    )
    normalized_max_expected_per_day = (
        quantize_quantity(max_expected_per_day)
        if max_expected_per_day is not None
        else None
    )
    normalized_current_stock = quantize_quantity(current_stock)
    normalized_expected_consumption = (
        quantize_quantity(expected_consumption_until_now)
        if expected_consumption_until_now is not None
        else None
    )
    normalized_actual_consumption = (
        quantize_quantity(actual_consumption_until_now)
        if actual_consumption_until_now is not None
        else None
    )

    days_remaining = None
    if normalized_daily_consumption > 0:
        days_remaining = quantize_ratio(
            normalized_current_stock / normalized_daily_consumption
        )

    divergence = None
    divergence_status = CalculationDivergenceStatus.NOT_AVAILABLE
    if (
        adherence_expected
        and normalized_expected_consumption is not None
        and normalized_actual_consumption is not None
    ):
        divergence = quantize_quantity(
            normalized_actual_consumption - normalized_expected_consumption
        )
        if abs(divergence) <= COHERENCE_TOLERANCE:
            divergence_status = CalculationDivergenceStatus.COHERENT
        elif divergence > 0:
            divergence_status = CalculationDivergenceStatus.ABOVE_EXPECTED
        else:
            divergence_status = CalculationDivergenceStatus.BELOW_EXPECTED

    status_result = classify_operational_status(
        usage_mode=usage_mode,
        comparison_window=comparison_window,
        daily_consumption=normalized_daily_consumption,
        current_stock=normalized_current_stock,
        days_remaining=days_remaining,
        expected_consumption_until_now=normalized_expected_consumption,
        actual_consumption_until_now=normalized_actual_consumption,
        divergence_status=divergence_status,
        adherence_expected=adherence_expected,
        administration_day_status=administration_day_status,
        administration_day_reason=administration_day_reason,
        invalid_reason_override=invalid_reason_override,
    )

    return CalculationEnginePayload(
        reference_date=reference_date,
        patient_id=patient_id,
        patient_name=patient_name,
        item_id=item_id,
        item_name=item_name,
        unit_symbol=unit_symbol,
        usage_mode=usage_mode,
        comparison_window=comparison_window,
        min_expected_per_day=normalized_min_expected_per_day,
        max_expected_per_day=normalized_max_expected_per_day,
        daily_consumption=normalized_daily_consumption,
        current_stock=normalized_current_stock,
        days_remaining=days_remaining,
        expected_consumption_until_now=normalized_expected_consumption,
        actual_consumption_until_now=normalized_actual_consumption,
        divergence=divergence,
        divergence_status=divergence_status,
        dose_occurrences=dose_occurrences,
        dose_schedule=dose_schedule,
        administration_day_status=administration_day_status,
        administration_day_reason=administration_day_reason,
        status=status_result.status,
        should_alert=status_result.should_alert,
        alert_reason=status_result.reason,
        is_valid=status_result.is_valid,
        invalid_reason=status_result.invalid_reason,
    )
