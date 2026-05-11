from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings


def get_project_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.app_timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def normalize_datetime_to_project_timezone(value: datetime) -> datetime:
    project_timezone = get_project_timezone()
    if value.tzinfo is None:
        return value.replace(tzinfo=project_timezone)
    return value.astimezone(project_timezone)


def get_current_datetime(
    *,
    current_datetime: datetime | None = None,
) -> datetime:
    if current_datetime is None:
        return datetime.now(get_project_timezone())
    return normalize_datetime_to_project_timezone(current_datetime)


def get_current_date(
    *,
    current_datetime: datetime | None = None,
) -> date:
    return get_current_datetime(current_datetime=current_datetime).date()
