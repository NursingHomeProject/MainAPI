from __future__ import annotations

from datetime import date, datetime, time

from app.core.clock import (
    get_current_datetime,
    get_project_timezone,
    normalize_datetime_to_project_timezone,
)

def resolve_reference_datetime(
    *,
    reference_date: date | None,
    reference_datetime: datetime | None = None,
    current_datetime: datetime | None = None,
) -> datetime:
    project_timezone = get_project_timezone()
    localized_now = get_current_datetime(current_datetime=current_datetime)

    if reference_datetime is None:
        localized_reference = localized_now
    else:
        localized_reference = normalize_datetime_to_project_timezone(reference_datetime)

    if reference_date is None:
        return localized_reference

    if reference_date < localized_now.date():
        return datetime.combine(reference_date, time.max).replace(
            tzinfo=project_timezone
        )

    if reference_date > localized_now.date():
        # The engine should not charge future doses before the day exists.
        return localized_now

    return localized_reference
