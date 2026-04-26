from __future__ import annotations

from decimal import Decimal

from app.modules.calculation.core.calculation import quantize_quantity, quantize_ratio
from app.modules.calculation.schemas import (
    CalculationDivergenceSnapshot,
    CalculationMetricsSnapshot,
)

DEFAULT_DIVERGENCE_THRESHOLD_PERCENT = Decimal("20")


def build_divergence_snapshot(
    metrics: CalculationMetricsSnapshot,
) -> CalculationDivergenceSnapshot:
    comparable = (
        metrics.predicted_daily_consumption > 0
        and metrics.realized_total_administration > 0
    )

    if not comparable:
        return CalculationDivergenceSnapshot(
            comparable=False,
            quantity_gap=None,
            percent_gap=None,
            default_threshold_percent=DEFAULT_DIVERGENCE_THRESHOLD_PERCENT,
            exceeds_default_threshold=False,
        )

    quantity_gap = quantize_quantity(
        metrics.realized_daily_average - metrics.predicted_daily_consumption
    )
    percent_gap = quantize_ratio(
        (quantity_gap / metrics.predicted_daily_consumption) * Decimal("100")
    )

    return CalculationDivergenceSnapshot(
        comparable=True,
        quantity_gap=quantity_gap,
        percent_gap=percent_gap,
        default_threshold_percent=DEFAULT_DIVERGENCE_THRESHOLD_PERCENT,
        exceeds_default_threshold=abs(percent_gap) >= DEFAULT_DIVERGENCE_THRESHOLD_PERCENT,
    )

