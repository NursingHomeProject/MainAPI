from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from app.core.clock import normalize_datetime_to_project_timezone
from app.modules.prescriptions.models import PrescriptionUsageMode


def parse_specific_times_safe(values: list[str] | None) -> list[time] | None:
    if not values:
        return None

    parsed_times: list[time] = []
    for raw_value in values:
        try:
            normalized_value = raw_value.strip()
            parsed_time = time.fromisoformat(normalized_value)
        except (AttributeError, TypeError, ValueError):
            return None

        parsed_times.append(parsed_time.replace(tzinfo=None))

    if len(set(parsed_times)) != len(parsed_times):
        return None

    return sorted(parsed_times)


def calculate_expected_fixed_consumption_until_now(
    prescription,
    *,
    reference_datetime: datetime,
) -> Decimal | None:
    usage_mode = getattr(prescription, "usage_mode", PrescriptionUsageMode.FIXED)
    if usage_mode != PrescriptionUsageMode.FIXED:
        return None

    specific_times = parse_specific_times_safe(
        getattr(prescription, "specific_times", None)
    )
    if not specific_times:
        return None

    frequency_per_day = getattr(prescription, "frequency_per_day", None)
    if frequency_per_day is None or len(specific_times) != int(frequency_per_day):
        return None

    start_date = getattr(prescription, "start_date", None)
    if start_date is None or start_date > reference_datetime.date():
        return Decimal("0")

    end_date = getattr(prescription, "end_date", None)
    if end_date is not None and end_date < reference_datetime.date():
        return Decimal("0")

    due_doses_in_window = sum(
        1
        for scheduled_time in specific_times
        if _is_scheduled_time_chargeable(
            prescription,
            scheduled_time=scheduled_time,
            reference_datetime=reference_datetime,
        )
    )
    return getattr(prescription, "dose_amount") * Decimal(due_doses_in_window)


def resolve_prescription_effective_start_datetime(
    prescription,
    *,
    reference_datetime: datetime,
) -> datetime | None:
    start_date = getattr(prescription, "start_date", None)
    if start_date is None:
        return None

    aligned_reference_datetime = _align_datetime_to_reference_context(
        reference_datetime,
        reference_datetime=reference_datetime,
    )
    scheduled_start_of_day = datetime.combine(
        start_date,
        time.min,
    ).replace(tzinfo=aligned_reference_datetime.tzinfo)

    created_at = getattr(prescription, "created_at", None)
    if created_at is None:
        return scheduled_start_of_day

    localized_created_at = _align_datetime_to_reference_context(
        created_at,
        reference_datetime=aligned_reference_datetime,
    )
    if localized_created_at.date() != start_date:
        return scheduled_start_of_day

    return max(scheduled_start_of_day, localized_created_at)


def resolve_prescription_effective_window_start(
    prescription,
    *,
    reference_datetime: datetime,
) -> datetime | None:
    effective_start_datetime = resolve_prescription_effective_start_datetime(
        prescription,
        reference_datetime=reference_datetime,
    )
    if effective_start_datetime is None:
        return None

    project_day_start = datetime.combine(
        reference_datetime.date(),
        time.min,
    ).replace(tzinfo=reference_datetime.tzinfo)
    return max(project_day_start, effective_start_datetime)


def _is_scheduled_time_chargeable(
    prescription,
    *,
    scheduled_time: time,
    reference_datetime: datetime,
) -> bool:
    scheduled_at = datetime.combine(
        reference_datetime.date(),
        scheduled_time,
    ).replace(tzinfo=reference_datetime.tzinfo)
    effective_window_start = resolve_prescription_effective_window_start(
        prescription,
        reference_datetime=reference_datetime,
    )
    if effective_window_start is not None and scheduled_at < effective_window_start:
        return False
    return scheduled_at <= reference_datetime


def _align_datetime_to_reference_context(
    value: datetime,
    *,
    reference_datetime: datetime,
) -> datetime:
    normalized_value = normalize_datetime_to_project_timezone(value)
    if reference_datetime.tzinfo is None:
        return normalized_value.replace(tzinfo=None)
    return normalized_value.astimezone(reference_datetime.tzinfo)
