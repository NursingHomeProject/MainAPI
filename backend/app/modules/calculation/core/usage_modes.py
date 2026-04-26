from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

from app.modules.calculation.core.fixed_usage import (
    parse_specific_times_safe,
    resolve_prescription_effective_window_start,
)
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)


@dataclass(frozen=True)
class UsageModeCalculationPlan:
    usage_mode: PrescriptionUsageMode | None
    comparison_window: PrescriptionComparisonWindow | None
    minimum_expected_per_day: Decimal | None
    maximum_expected_per_day: Decimal | None
    daily_consumption: Decimal
    exact_expected_consumption_until_now: Decimal | None
    expected_min_until_now: Decimal | None
    expected_max_until_now: Decimal | None
    actual_window_start: datetime | None
    actual_window_end: datetime | None
    use_dose_occurrences: bool
    schedule_invalid_reason: str | None
    adherence_expected: bool
    invalid_reason: str | None


def resolve_usage_mode_plan(
    prescriptions,
    *,
    reference_datetime: datetime,
) -> UsageModeCalculationPlan:
    if not prescriptions:
        return UsageModeCalculationPlan(
            usage_mode=None,
            comparison_window=None,
            minimum_expected_per_day=None,
            maximum_expected_per_day=None,
            daily_consumption=Decimal("0"),
            exact_expected_consumption_until_now=None,
            expected_min_until_now=None,
            expected_max_until_now=None,
            actual_window_start=None,
            actual_window_end=reference_datetime,
            use_dose_occurrences=False,
            schedule_invalid_reason=None,
            adherence_expected=True,
            invalid_reason=None,
        )

    usage_modes = {
        getattr(prescription, "usage_mode", PrescriptionUsageMode.FIXED)
        for prescription in prescriptions
    }
    if len(usage_modes) != 1:
        return UsageModeCalculationPlan(
            usage_mode=None,
            comparison_window=None,
            minimum_expected_per_day=None,
            maximum_expected_per_day=None,
            daily_consumption=Decimal("0"),
            exact_expected_consumption_until_now=None,
            expected_min_until_now=None,
            expected_max_until_now=None,
            actual_window_start=None,
            actual_window_end=reference_datetime,
            use_dose_occurrences=False,
            schedule_invalid_reason=None,
            adherence_expected=True,
            invalid_reason="Prescricoes ativas do mesmo item usam modos de acompanhamento diferentes.",
        )

    usage_mode = next(iter(usage_modes))

    if usage_mode == PrescriptionUsageMode.FIXED:
        return _build_fixed_usage_plan(
            prescriptions,
            reference_datetime=reference_datetime,
        )
    if usage_mode == PrescriptionUsageMode.VARIABLE:
        return _build_variable_usage_plan(
            prescriptions,
            reference_datetime=reference_datetime,
        )
    return _build_on_demand_usage_plan(
        prescriptions,
        reference_datetime=reference_datetime,
    )


def resolve_expected_consumption_for_plan(
    plan: UsageModeCalculationPlan,
    *,
    actual_consumption_until_now: Decimal | None,
) -> Decimal | None:
    if not plan.adherence_expected:
        return None

    if plan.exact_expected_consumption_until_now is not None:
        return plan.exact_expected_consumption_until_now

    if (
        plan.expected_min_until_now is None
        or plan.expected_max_until_now is None
        or actual_consumption_until_now is None
    ):
        return plan.expected_min_until_now

    if actual_consumption_until_now < plan.expected_min_until_now:
        return plan.expected_min_until_now
    if actual_consumption_until_now > plan.expected_max_until_now:
        return plan.expected_max_until_now
    return actual_consumption_until_now


def _build_fixed_usage_plan(
    prescriptions,
    *,
    reference_datetime: datetime,
) -> UsageModeCalculationPlan:
    daily_consumption = Decimal("0")
    raw_comparison_window = _resolve_comparison_window_for_mode(
        prescriptions,
        default_window=PrescriptionComparisonWindow.DAILY_TOTAL,
    )
    if raw_comparison_window is None:
        return _build_invalid_mode_plan(
            usage_mode=PrescriptionUsageMode.FIXED,
            invalid_reason="Prescricoes fixas do mesmo item usam janelas de comparacao diferentes.",
            reference_datetime=reference_datetime,
        )

    comparison_window = _normalize_fixed_comparison_window(
        prescriptions,
        raw_comparison_window=raw_comparison_window,
    )
    exact_expected = Decimal("0")
    day_window_start = datetime.combine(
        reference_datetime.date(),
        time.min,
    ).replace(tzinfo=reference_datetime.tzinfo)
    actual_window_start = None
    use_dose_occurrences = False
    schedule_invalid_reason = None

    for prescription in prescriptions:
        daily_consumption += (
            prescription.dose_amount * Decimal(prescription.frequency_per_day)
        )

        if not _is_prescription_active_on_reference_date(
            prescription,
            reference_datetime=reference_datetime,
        ):
            continue

        effective_window_start = resolve_prescription_effective_window_start(
            prescription,
            reference_datetime=reference_datetime,
        )
        if effective_window_start is not None:
            if actual_window_start is None:
                actual_window_start = effective_window_start
            else:
                actual_window_start = min(actual_window_start, effective_window_start)

        if comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES:
            if _prescription_supports_scheduled_times(prescription):
                use_dose_occurrences = True
                continue
            schedule_invalid_reason = (
                "Prescricao fixa configurada para comparacao por horario sem horarios validos."
            )

        exact_expected += _calculate_fixed_daily_total_expected_in_window(
            prescription,
            reference_datetime=reference_datetime,
        )

    return UsageModeCalculationPlan(
        usage_mode=PrescriptionUsageMode.FIXED,
        comparison_window=comparison_window,
        minimum_expected_per_day=None,
        maximum_expected_per_day=None,
        daily_consumption=daily_consumption,
        exact_expected_consumption_until_now=(
            None if use_dose_occurrences else exact_expected
        ),
        expected_min_until_now=None,
        expected_max_until_now=None,
        actual_window_start=actual_window_start or day_window_start,
        actual_window_end=reference_datetime,
        use_dose_occurrences=use_dose_occurrences,
        schedule_invalid_reason=schedule_invalid_reason,
        adherence_expected=True,
        invalid_reason=None,
    )


def _build_variable_usage_plan(
    prescriptions,
    *,
    reference_datetime: datetime,
) -> UsageModeCalculationPlan:
    raw_comparison_window = _resolve_comparison_window_for_mode(
        prescriptions,
        default_window=PrescriptionComparisonWindow.ROLLING_24H,
    )
    if raw_comparison_window is None:
        return _build_invalid_mode_plan(
            usage_mode=PrescriptionUsageMode.VARIABLE,
            invalid_reason="Prescricoes variaveis do mesmo item usam janelas de comparacao diferentes.",
            reference_datetime=reference_datetime,
        )
    comparison_window = _normalize_variable_comparison_window(raw_comparison_window)

    daily_consumption = Decimal("0")
    minimum_daily = Decimal("0")
    maximum_daily = Decimal("0")

    for prescription in prescriptions:
        minimum_for_prescription = _resolve_min_expected_per_day(prescription)
        maximum_for_prescription = _resolve_max_expected_per_day(prescription)

        if maximum_for_prescription < minimum_for_prescription:
            return _build_invalid_mode_plan(
                usage_mode=PrescriptionUsageMode.VARIABLE,
                invalid_reason="A faixa esperada da prescricao variavel esta inconsistente.",
                reference_datetime=reference_datetime,
            )

        minimum_daily += minimum_for_prescription
        maximum_daily += maximum_for_prescription
        daily_consumption += maximum_for_prescription

    factor, actual_window_start = _resolve_window_factor_and_start(
        comparison_window=comparison_window,
        reference_datetime=reference_datetime,
    )

    return UsageModeCalculationPlan(
        usage_mode=PrescriptionUsageMode.VARIABLE,
        comparison_window=comparison_window,
        minimum_expected_per_day=minimum_daily,
        maximum_expected_per_day=maximum_daily,
        daily_consumption=daily_consumption,
        exact_expected_consumption_until_now=None,
        expected_min_until_now=minimum_daily * factor,
        expected_max_until_now=maximum_daily * factor,
        actual_window_start=actual_window_start,
        actual_window_end=reference_datetime,
        use_dose_occurrences=False,
        schedule_invalid_reason=None,
        adherence_expected=True,
        invalid_reason=None,
    )


def _build_on_demand_usage_plan(
    prescriptions,
    *,
    reference_datetime: datetime,
) -> UsageModeCalculationPlan:
    comparison_window = _resolve_comparison_window_for_mode(
        prescriptions,
        default_window=PrescriptionComparisonWindow.ROLLING_24H,
    )
    if comparison_window is None:
        return _build_invalid_mode_plan(
            usage_mode=PrescriptionUsageMode.ON_DEMAND,
            invalid_reason="Prescricoes sob demanda do mesmo item usam janelas de comparacao diferentes.",
            reference_datetime=reference_datetime,
        )

    daily_consumption = Decimal("0")
    minimum_daily: Decimal | None = Decimal("0")
    has_any_minimum = False
    maximum_daily = Decimal("0")
    for prescription in prescriptions:
        explicit_minimum = getattr(prescription, "min_expected_per_day", None)
        if explicit_minimum is not None:
            if minimum_daily is not None:
                minimum_daily += explicit_minimum
            has_any_minimum = True
        maximum_for_prescription = _resolve_max_expected_per_day(prescription)
        maximum_daily += maximum_for_prescription
        daily_consumption += maximum_for_prescription

    _, actual_window_start = _resolve_window_factor_and_start(
        comparison_window=comparison_window,
        reference_datetime=reference_datetime,
    )

    return UsageModeCalculationPlan(
        usage_mode=PrescriptionUsageMode.ON_DEMAND,
        comparison_window=comparison_window,
        minimum_expected_per_day=minimum_daily if has_any_minimum else None,
        maximum_expected_per_day=maximum_daily,
        daily_consumption=daily_consumption,
        exact_expected_consumption_until_now=None,
        expected_min_until_now=None,
        expected_max_until_now=None,
        actual_window_start=actual_window_start,
        actual_window_end=reference_datetime,
        use_dose_occurrences=False,
        schedule_invalid_reason=None,
        adherence_expected=False,
        invalid_reason=None,
    )


def _build_invalid_mode_plan(
    *,
    usage_mode: PrescriptionUsageMode,
    invalid_reason: str,
    reference_datetime: datetime,
) -> UsageModeCalculationPlan:
    return UsageModeCalculationPlan(
        usage_mode=usage_mode,
        comparison_window=None,
        minimum_expected_per_day=None,
        maximum_expected_per_day=None,
        daily_consumption=Decimal("0"),
        exact_expected_consumption_until_now=None,
        expected_min_until_now=None,
        expected_max_until_now=None,
        actual_window_start=None,
        actual_window_end=reference_datetime,
        use_dose_occurrences=False,
        schedule_invalid_reason=None,
        adherence_expected=True,
        invalid_reason=invalid_reason,
    )


def _resolve_comparison_window_for_mode(
    prescriptions,
    *,
    default_window: PrescriptionComparisonWindow,
) -> PrescriptionComparisonWindow | None:
    windows = {
        getattr(prescription, "comparison_window", default_window)
        for prescription in prescriptions
    }
    if len(windows) != 1:
        return None
    return next(iter(windows))


def _resolve_min_expected_per_day(prescription) -> Decimal:
    explicit_minimum = getattr(prescription, "min_expected_per_day", None)
    if explicit_minimum is not None:
        return explicit_minimum
    return prescription.dose_amount * Decimal(prescription.frequency_per_day)


def _normalize_variable_comparison_window(
    comparison_window: PrescriptionComparisonWindow,
) -> PrescriptionComparisonWindow:
    # Variable supplies such as diapers are compared by range in an operational
    # window, never by rigid dose times. If legacy data still points to
    # scheduled_times, we safely fall back to daily_total for the MVP.
    if comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES:
        return PrescriptionComparisonWindow.DAILY_TOTAL
    return comparison_window


def _resolve_max_expected_per_day(prescription) -> Decimal:
    explicit_maximum = getattr(prescription, "max_expected_per_day", None)
    if explicit_maximum is not None:
        return explicit_maximum
    explicit_minimum = getattr(prescription, "min_expected_per_day", None)
    if explicit_minimum is not None:
        return explicit_minimum
    return prescription.dose_amount * Decimal(prescription.frequency_per_day)


def _normalize_fixed_comparison_window(
    prescriptions,
    *,
    raw_comparison_window: PrescriptionComparisonWindow,
) -> PrescriptionComparisonWindow:
    supports_scheduled_times = all(
        _prescription_supports_scheduled_times(prescription)
        for prescription in prescriptions
    )

    if raw_comparison_window in {
        PrescriptionComparisonWindow.ROLLING_24H,
        PrescriptionComparisonWindow.SHIFT_WINDOW,
    }:
        return PrescriptionComparisonWindow.DAILY_TOTAL

    if (
        raw_comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
        and not supports_scheduled_times
    ):
        return PrescriptionComparisonWindow.DAILY_TOTAL

    return raw_comparison_window


def _prescription_supports_scheduled_times(prescription) -> bool:
    specific_times = parse_specific_times_safe(
        getattr(prescription, "specific_times", None)
    )
    if not specific_times:
        return False

    frequency_per_day = getattr(prescription, "frequency_per_day", None)
    if frequency_per_day is None:
        return False

    return len(specific_times) == int(frequency_per_day)


def _is_prescription_active_on_reference_date(
    prescription,
    *,
    reference_datetime: datetime,
) -> bool:
    start_date = getattr(prescription, "start_date", None)
    if start_date is None or start_date > reference_datetime.date():
        return False

    end_date = getattr(prescription, "end_date", None)
    if end_date is not None and end_date < reference_datetime.date():
        return False

    return True


def _calculate_fixed_daily_total_expected_in_window(
    prescription,
    *,
    reference_datetime: datetime,
) -> Decimal:
    if not _is_prescription_active_on_reference_date(
        prescription,
        reference_datetime=reference_datetime,
    ):
        return Decimal("0")

    daily_total = prescription.dose_amount * Decimal(prescription.frequency_per_day)
    if reference_datetime.time() == time.max:
        effective_window_start = resolve_prescription_effective_window_start(
            prescription,
            reference_datetime=reference_datetime,
        )
        if effective_window_start is None:
            return daily_total
        next_day_start = datetime.combine(
            reference_datetime.date() + timedelta(days=1),
            time.min,
        ).replace(tzinfo=reference_datetime.tzinfo)
        elapsed_seconds = max(
            (next_day_start - effective_window_start).total_seconds(),
            0,
        )
        factor = Decimal(str(elapsed_seconds / 86400))
        return daily_total * factor

    effective_window_start = resolve_prescription_effective_window_start(
        prescription,
        reference_datetime=reference_datetime,
    )
    if effective_window_start is None:
        return Decimal("0")
    elapsed_seconds = max(
        (reference_datetime - effective_window_start).total_seconds(),
        0,
    )
    factor = Decimal(str(elapsed_seconds / 86400))
    return daily_total * factor


def _resolve_window_factor_and_start(
    *,
    comparison_window: PrescriptionComparisonWindow,
    reference_datetime: datetime,
) -> tuple[Decimal, datetime]:
    project_day_start = datetime.combine(
        reference_datetime.date(),
        time.min,
    ).replace(tzinfo=reference_datetime.tzinfo)

    if comparison_window == PrescriptionComparisonWindow.ROLLING_24H:
        return Decimal("1"), reference_datetime - timedelta(hours=24)

    if comparison_window == PrescriptionComparisonWindow.SHIFT_WINDOW:
        if reference_datetime.hour < 8:
            shift_start_hour = 0
        elif reference_datetime.hour < 16:
            shift_start_hour = 8
        else:
            shift_start_hour = 16

        shift_start = datetime.combine(
            reference_datetime.date(),
            time(hour=shift_start_hour),
        ).replace(tzinfo=reference_datetime.tzinfo)
        elapsed_seconds = max((reference_datetime - shift_start).total_seconds(), 0)
        return (
            Decimal(str(elapsed_seconds / 86400)),
            shift_start,
        )

    if reference_datetime.time() == time.max:
        return Decimal("1"), project_day_start

    elapsed_seconds = max((reference_datetime - project_day_start).total_seconds(), 0)
    return (
        Decimal(str(elapsed_seconds / 86400)),
        project_day_start,
    )
