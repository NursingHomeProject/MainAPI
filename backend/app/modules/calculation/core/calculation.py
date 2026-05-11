from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.modules.calculation.core.sources import CalculationSourceRow
from app.modules.calculation.schemas import (
    CalculationAvailabilitySnapshot,
    CalculationMetricsSnapshot,
)

QUANTITY_PRECISION = Decimal("0.001")
RATIO_PRECISION = Decimal("0.01")


def quantize_quantity(value: Decimal) -> Decimal:
    return value.quantize(QUANTITY_PRECISION, rounding=ROUND_HALF_UP)


def quantize_ratio(value: Decimal) -> Decimal:
    return value.quantize(RATIO_PRECISION, rounding=ROUND_HALF_UP)


def build_metrics_snapshot(
    source: CalculationSourceRow,
    *,
    window_days: int,
) -> CalculationMetricsSnapshot:
    predicted_daily_consumption = quantize_quantity(source.predicted_daily_consumption)
    current_stock = quantize_quantity(source.current_stock)
    minimum_stock = quantize_quantity(source.minimum_stock)
    realized_total_administration = quantize_quantity(source.realized_total_administration)
    realized_daily_average = quantize_quantity(
        realized_total_administration / Decimal(window_days)
    )

    days_remaining = None
    if predicted_daily_consumption > 0:
        days_remaining = quantize_ratio(current_stock / predicted_daily_consumption)

    return CalculationMetricsSnapshot(
        current_stock=current_stock,
        minimum_stock=minimum_stock,
        active_prescriptions=source.active_prescriptions,
        predicted_daily_consumption=predicted_daily_consumption,
        realized_total_administration=realized_total_administration,
        realized_daily_average=realized_daily_average,
        realized_window_days=window_days,
        days_remaining=days_remaining,
    )


def build_availability_snapshot(
    metrics: CalculationMetricsSnapshot,
    *,
    divergence_available: bool,
    status_context_available: bool,
) -> CalculationAvailabilitySnapshot:
    return CalculationAvailabilitySnapshot(
        stock_available=True,
        predicted_consumption_available=metrics.predicted_daily_consumption > 0,
        realized_consumption_available=metrics.realized_total_administration > 0,
        days_remaining_available=metrics.days_remaining is not None,
        divergence_available=divergence_available,
        status_context_available=status_context_available,
        alert_context_available=status_context_available,
    )

