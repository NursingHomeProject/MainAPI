from __future__ import annotations

from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.core.clock import (
    get_current_date,
    get_current_datetime,
    normalize_datetime_to_project_timezone,
)
from app.modules.calculation.core.timing import resolve_reference_datetime


class ClockTests(TestCase):
    project_timezone = ZoneInfo("America/Sao_Paulo")

    def test_normalize_datetime_to_project_timezone_interprets_naive_value_as_local(self) -> None:
        value = datetime(2026, 4, 12, 10, 0)

        normalized_value = normalize_datetime_to_project_timezone(value)

        self.assertEqual(normalized_value.tzinfo, self.project_timezone)
        self.assertEqual(normalized_value.hour, 10)

    def test_normalize_datetime_to_project_timezone_converts_aware_value(self) -> None:
        value = datetime(2026, 4, 12, 13, 0, tzinfo=ZoneInfo("UTC"))

        normalized_value = normalize_datetime_to_project_timezone(value)

        self.assertEqual(normalized_value.tzinfo, self.project_timezone)
        self.assertEqual(normalized_value.hour, 10)

    def test_get_current_date_uses_project_clock(self) -> None:
        mocked_now = datetime(2026, 4, 12, 23, 30, tzinfo=self.project_timezone)

        returned_date = get_current_date(current_datetime=mocked_now)

        self.assertEqual(returned_date, date(2026, 4, 12))

    def test_get_current_datetime_converts_utc_near_midnight_to_project_timezone(self) -> None:
        mocked_now = datetime(2026, 4, 13, 2, 30, tzinfo=ZoneInfo("UTC"))

        returned_datetime = get_current_datetime(current_datetime=mocked_now)

        self.assertEqual(returned_datetime.tzinfo, self.project_timezone)
        self.assertEqual(returned_datetime.date(), date(2026, 4, 12))
        self.assertEqual(returned_datetime.hour, 23)
        self.assertEqual(returned_datetime.minute, 30)

    def test_resolve_reference_datetime_uses_injected_now_for_future_dates(self) -> None:
        mocked_now = datetime(2026, 4, 12, 10, 0, tzinfo=self.project_timezone)

        resolved_reference = resolve_reference_datetime(
            reference_date=date(2026, 4, 13),
            current_datetime=mocked_now,
        )

        self.assertEqual(resolved_reference, mocked_now)

    def test_resolve_reference_datetime_closes_past_dates_at_end_of_day(self) -> None:
        mocked_now = datetime(2026, 4, 12, 10, 0, tzinfo=self.project_timezone)

        resolved_reference = resolve_reference_datetime(
            reference_date=date(2026, 4, 10),
            current_datetime=mocked_now,
        )

        self.assertEqual(resolved_reference.date(), date(2026, 4, 10))
        self.assertEqual(resolved_reference.hour, 23)
        self.assertEqual(resolved_reference.minute, 59)
