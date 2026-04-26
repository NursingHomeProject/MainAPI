from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from app.modules.calculation.schemas import (
    CalculationAdministrationDayStatus,
    CalculationDivergenceStatus,
    CalculationDivergenceSnapshot,
    CalculationMetricsSnapshot,
    CalculationOperationalStatus,
    CalculationStatusContextSnapshot,
)
from app.modules.prescriptions.models import PrescriptionUsageMode
from app.modules.prescriptions.models import PrescriptionComparisonWindow

LOW_STOCK_DAYS_THRESHOLD = Decimal("7")
CRITICAL_STOCK_DAYS_THRESHOLD = Decimal("3")


class OperationalStatusResult(NamedTuple):
    status: CalculationOperationalStatus
    should_alert: bool
    reason: str | None
    is_valid: bool
    invalid_reason: str | None


def build_status_context_snapshot(
    metrics: CalculationMetricsSnapshot,
    divergence: CalculationDivergenceSnapshot,
) -> CalculationStatusContextSnapshot:
    has_prediction = metrics.predicted_daily_consumption > 0
    has_realized_history = metrics.realized_total_administration > 0

    return CalculationStatusContextSnapshot(
        below_minimum_stock=metrics.current_stock < metrics.minimum_stock,
        out_of_stock=metrics.current_stock <= 0,
        has_prediction=has_prediction,
        has_realized_history=has_realized_history,
        days_remaining=metrics.days_remaining,
        divergence_detected=divergence.exceeds_default_threshold,
        ready_for_status_classification=has_prediction or divergence.comparable,
    )


def classify_operational_status(
    *,
    usage_mode: PrescriptionUsageMode | None,
    comparison_window: PrescriptionComparisonWindow | None,
    daily_consumption: Decimal,
    current_stock: Decimal,
    days_remaining: Decimal | None,
    expected_consumption_until_now: Decimal | None,
    actual_consumption_until_now: Decimal | None,
    divergence_status: CalculationDivergenceStatus,
    adherence_expected: bool,
    administration_day_status: CalculationAdministrationDayStatus | None = None,
    administration_day_reason: str | None = None,
    invalid_reason_override: str | None = None,
) -> OperationalStatusResult:
    # Priority is intentionally linear and exclusive:
    # 1. invalid_prescription -> no valid daily prediction can be trusted
    # 2. inconsistent_data -> there is a calculation context, but the data does not close cleanly
    # 3. critical_stock -> urgent stock shortage has priority over divergence
    # 4. low_stock -> attention on stock before consumption drift
    # 5. consumption_above_expected / consumption_below_expected -> operational deviation
    # 6. ok -> none of the higher-priority conditions were triggered
    adherence_required = (
        adherence_expected and usage_mode != PrescriptionUsageMode.ON_DEMAND
    )
    scheduled_dose_tracking_enabled = (
        usage_mode == PrescriptionUsageMode.FIXED
        and comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
    )

    if invalid_reason_override is not None:
        return OperationalStatusResult(
            status=CalculationOperationalStatus.INVALID_PRESCRIPTION,
            should_alert=True,
            reason=invalid_reason_override,
            is_valid=False,
            invalid_reason=invalid_reason_override,
        )

    if adherence_required and (
        daily_consumption <= 0 or expected_consumption_until_now is None
    ):
        reason = (
            "Nao foi possivel validar a prescricao ativa para calcular o consumo previsto."
        )
        return OperationalStatusResult(
            status=CalculationOperationalStatus.INVALID_PRESCRIPTION,
            should_alert=True,
            reason=reason,
            is_valid=False,
            invalid_reason=reason,
        )

    if (
        current_stock < 0
        or (adherence_required and actual_consumption_until_now is None)
        or (days_remaining is not None and days_remaining < 0)
    ):
        reason = "Os dados atuais do item estao inconsistentes para classificacao operacional."
        return OperationalStatusResult(
            status=CalculationOperationalStatus.INCONSISTENT_DATA,
            should_alert=True,
            reason=reason,
            is_valid=False,
            invalid_reason=reason,
        )

    if current_stock <= 0 or (
        days_remaining is not None and days_remaining <= CRITICAL_STOCK_DAYS_THRESHOLD
    ):
        return OperationalStatusResult(
            status=CalculationOperationalStatus.CRITICAL_STOCK,
            should_alert=True,
            reason=_build_stock_reason(
                usage_mode=usage_mode,
                critical=True,
            ),
            is_valid=True,
            invalid_reason=None,
        )

    if days_remaining is not None and days_remaining <= LOW_STOCK_DAYS_THRESHOLD:
        return OperationalStatusResult(
            status=CalculationOperationalStatus.LOW_STOCK,
            should_alert=True,
            reason=_build_stock_reason(
                usage_mode=usage_mode,
                critical=False,
            ),
            is_valid=True,
            invalid_reason=None,
        )

    if scheduled_dose_tracking_enabled:
        if administration_day_status == CalculationAdministrationDayStatus.MISSED_DOSE:
            return OperationalStatusResult(
                status=CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
                should_alert=True,
                reason=_build_scheduled_dose_alert_reason(administration_day_reason),
                is_valid=True,
                invalid_reason=None,
            )

        if (
            adherence_required
            and divergence_status == CalculationDivergenceStatus.ABOVE_EXPECTED
        ):
            return OperationalStatusResult(
                status=CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED,
                should_alert=True,
                reason=_build_divergence_reason(
                    usage_mode=usage_mode,
                    comparison_window=comparison_window,
                    divergence_status=divergence_status,
                ),
                is_valid=True,
                invalid_reason=None,
            )

        return OperationalStatusResult(
            status=CalculationOperationalStatus.OK,
            should_alert=False,
            reason=None,
            is_valid=True,
            invalid_reason=None,
        )

    if adherence_required and divergence_status == CalculationDivergenceStatus.ABOVE_EXPECTED:
        return OperationalStatusResult(
            status=CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED,
            should_alert=True,
            reason=_build_divergence_reason(
                usage_mode=usage_mode,
                comparison_window=comparison_window,
                divergence_status=divergence_status,
            ),
            is_valid=True,
            invalid_reason=None,
        )

    if adherence_required and divergence_status == CalculationDivergenceStatus.BELOW_EXPECTED:
        return OperationalStatusResult(
            status=CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
            should_alert=True,
            reason=_build_divergence_reason(
                usage_mode=usage_mode,
                comparison_window=comparison_window,
                divergence_status=divergence_status,
            ),
            is_valid=True,
            invalid_reason=None,
        )

    return OperationalStatusResult(
        status=CalculationOperationalStatus.OK,
        should_alert=False,
        reason=None,
        is_valid=True,
        invalid_reason=None,
    )


def _build_stock_reason(
    *,
    usage_mode: PrescriptionUsageMode | None,
    critical: bool,
) -> str:
    if usage_mode == PrescriptionUsageMode.ON_DEMAND:
        return (
            "Saldo em faixa critica para uso sob demanda."
            if critical
            else "Saldo em faixa de atencao para uso sob demanda."
        )

    return (
        "Saldo em faixa critica para operacao."
        if critical
        else "Saldo em faixa de atencao para reposicao."
    )


def _build_scheduled_dose_alert_reason(
    administration_day_reason: str | None,
) -> str:
    if administration_day_reason:
        return administration_day_reason
    return "Existe dose atrasada sem registro de administracao apos a tolerancia configurada."


def _build_divergence_reason(
    *,
    usage_mode: PrescriptionUsageMode | None,
    comparison_window: PrescriptionComparisonWindow | None,
    divergence_status: CalculationDivergenceStatus,
) -> str:
    if usage_mode == PrescriptionUsageMode.VARIABLE:
        return (
            "Uso acima da faixa esperada na janela operacional."
            if divergence_status == CalculationDivergenceStatus.ABOVE_EXPECTED
            else "Uso abaixo da faixa esperada na janela operacional."
        )

    if comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES:
        return (
            "Consumo acima do previsto para os horarios ja decorridos."
            if divergence_status == CalculationDivergenceStatus.ABOVE_EXPECTED
            else "Consumo abaixo do previsto para os horarios ja decorridos."
        )

    return (
        "Consumo acima do esperado na janela atual."
        if divergence_status == CalculationDivergenceStatus.ABOVE_EXPECTED
        else "Consumo abaixo do esperado na janela atual."
    )
