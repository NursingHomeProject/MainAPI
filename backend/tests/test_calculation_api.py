from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.modules.auth.dependencies import get_current_active_user
from app.modules.calculation.core.dose_schedule import DoseAdministrationRecord
from app.modules.internal_alerts.models import AlertStatus
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)


class CalculationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sentinel_db = object()
        self.fake_user = SimpleNamespace(id=uuid4(), is_active=True)
        self.patient_id = uuid4()
        self.item_id = uuid4()
        self.now = datetime.now(timezone.utc)
        self.alerts_store: list[SimpleNamespace] = []

        self.patients = {
            self.patient_id: SimpleNamespace(
                id=self.patient_id,
                full_name="Maria da Conceicao",
            )
        }
        self.items = {
            self.item_id: SimpleNamespace(
                id=self.item_id,
                name="Dipirona 500mg",
                unit=SimpleNamespace(symbol="comprimido"),
            )
        }
        self.prescriptions_map = {
            (self.patient_id, self.item_id): [
                SimpleNamespace(
                    dose_amount=Decimal("1"),
                    frequency_per_day=3,
                    specific_times=None,
                    usage_mode=PrescriptionUsageMode.FIXED,
                    comparison_window=PrescriptionComparisonWindow.DAILY_TOTAL,
                    min_expected_per_day=None,
                    max_expected_per_day=None,
                    start_date=date(2026, 4, 1),
                    end_date=None,
                )
            ]
        }
        self.actual_map = {(self.patient_id, self.item_id): Decimal("3")}
        self.administration_records_map = {(self.patient_id, self.item_id): []}
        self.stock_map = {self.item_id: Decimal("18")}

        app.dependency_overrides[get_db] = self._override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: self.fake_user

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _override_get_db(self):
        yield self.sentinel_db

    def _fake_get_patient_or_raise(self, db, requested_patient_id):
        return self.patients[requested_patient_id]

    def _fake_get_item_or_raise(self, db, requested_item_id):
        return self.items[requested_item_id]

    def _fake_list_active_prescriptions_for_patient_item(
        self,
        db,
        *,
        patient_id,
        item_id,
        reference_date,
    ):
        return self.prescriptions_map.get((patient_id, item_id), [])

    def _fake_calculate_actual_consumption_until_now(
        self,
        db,
        *,
        patient_id,
        item_id,
        window_start,
        window_end,
    ):
        return self.actual_map.get((patient_id, item_id), Decimal("0"))

    def _fake_calculate_current_stock_for_item(self, db, requested_item_id):
        return self.stock_map.get(requested_item_id, Decimal("0"))

    def _fake_list_administration_records_until_now(
        self,
        db,
        *,
        patient_id,
        item_id,
        window_start,
        window_end,
    ):
        return self.administration_records_map.get((patient_id, item_id), [])

    def _fake_list_active_projection_pairs(
        self,
        db,
        *,
        reference_date,
        patient_id=None,
        item_id=None,
    ):
        pairs = list(self.prescriptions_map.keys())
        if patient_id is not None:
            pairs = [pair for pair in pairs if pair[0] == patient_id]
        if item_id is not None:
            pairs = [pair for pair in pairs if pair[1] == item_id]
        return pairs

    def _fake_list_open_alerts_by_type(self, db, *, alert_type):
        return [
            alert
            for alert in self.alerts_store
            if alert.alert_type == alert_type and alert.status == AlertStatus.OPEN
        ]

    def _fake_create_alert(self, db, payload):
        alert = SimpleNamespace(
            id=uuid4(),
            item_id=payload.item_id,
            patient_id=payload.patient_id,
            resolved_by_user_id=None,
            alert_type=payload.alert_type,
            title=payload.title,
            reason=payload.reason,
            message=payload.message,
            severity=payload.severity,
            status=AlertStatus.OPEN,
            resolved_at=None,
            created_at=self.now,
            updated_at=self.now,
        )
        self.alerts_store.append(alert)
        return alert

    def _fake_update_alert_content(self, db, alert, *, title, reason, message, severity):
        alert.title = title
        alert.reason = reason
        alert.message = message
        alert.severity = severity
        alert.updated_at = datetime.now(timezone.utc)
        return alert

    def _fake_find_equivalent_open_alert(self, db, payload):
        for alert in self.alerts_store:
            if alert.status != AlertStatus.OPEN:
                continue
            if alert.alert_type != payload.alert_type:
                continue
            if alert.patient_id != payload.patient_id:
                continue
            if alert.item_id != payload.item_id:
                continue
            return alert
        return None

    def _fake_resolve_alert(self, db, alert, *, resolved_by_user_id=None):
        alert.status = AlertStatus.RESOLVED
        alert.resolved_by_user_id = resolved_by_user_id
        alert.resolved_at = datetime.now(timezone.utc)
        alert.updated_at = datetime.now(timezone.utc)
        return alert

    def _fake_list_alerts(
        self,
        db,
        *,
        status_filter=None,
        severity_filter=None,
        alert_type_filter=None,
        patient_id=None,
        item_id=None,
    ):
        alerts = self.alerts_store
        if status_filter is not None:
            alerts = [alert for alert in alerts if alert.status == status_filter]
        if severity_filter is not None:
            alerts = [alert for alert in alerts if alert.severity == severity_filter]
        if alert_type_filter is not None:
            alerts = [alert for alert in alerts if alert.alert_type == alert_type_filter]
        if patient_id is not None:
            alerts = [alert for alert in alerts if alert.patient_id == patient_id]
        if item_id is not None:
            alerts = [alert for alert in alerts if alert.item_id == item_id]
        return alerts

    def _set_fixed_scheduled_context(
        self,
        *,
        patient_id=None,
        item_id=None,
        item_name: str | None = None,
        specific_times: list[str],
        frequency_per_day: int,
        actual_consumption: str,
        current_stock: str,
        administration_times: list[str] | None = None,
        administration_timestamps: list[str] | None = None,
        start_date_value: date = date(2026, 4, 10),
        created_at_value: datetime | None = None,
    ) -> None:
        resolved_patient_id = patient_id or self.patient_id
        resolved_item_id = item_id or self.item_id
        prescription_id = uuid4()
        self.prescriptions_map[(resolved_patient_id, resolved_item_id)] = [
            SimpleNamespace(
                id=prescription_id,
                dose_amount=Decimal("1"),
                frequency_per_day=frequency_per_day,
                specific_times=specific_times,
                usage_mode=PrescriptionUsageMode.FIXED,
                comparison_window=PrescriptionComparisonWindow.SCHEDULED_TIMES,
                min_expected_per_day=None,
                max_expected_per_day=None,
                start_date=start_date_value,
                end_date=None,
                created_at=created_at_value,
            )
        ]
        self.actual_map[(resolved_patient_id, resolved_item_id)] = Decimal(actual_consumption)
        scheduled_administration_datetimes = administration_timestamps or [
            f"2026-04-10T{scheduled_time}:00+00:00"
            for scheduled_time in (administration_times or [])
        ]
        self.administration_records_map[(resolved_patient_id, resolved_item_id)] = [
            DoseAdministrationRecord(
                occurred_at=datetime.fromisoformat(occurred_at_value),
                quantity=Decimal("1"),
                prescription_id=prescription_id,
            )
            for occurred_at_value in scheduled_administration_datetimes
        ]
        self.stock_map[resolved_item_id] = Decimal(current_stock)
        if resolved_patient_id not in self.patients:
            self.patients[resolved_patient_id] = SimpleNamespace(
                id=resolved_patient_id,
                full_name=f"Paciente {str(resolved_patient_id)[:8]}",
            )
        if resolved_item_id not in self.items:
            self.items[resolved_item_id] = SimpleNamespace(
                id=resolved_item_id,
                name=item_name or f"Item {str(resolved_item_id)[:8]}",
                unit=SimpleNamespace(symbol="comprimido"),
            )

    def test_projection_endpoint_returns_real_engine_payload(self):
        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-08"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["daily_consumption"], "3.000")
        self.assertEqual(payload["current_stock"], "18.000")
        self.assertEqual(payload["comparison_window"], "daily_total")
        self.assertIsNone(payload["min_expected_per_day"])
        self.assertIsNone(payload["max_expected_per_day"])
        self.assertIsNone(payload["dose_schedule"])
        self.assertEqual(payload["expected_consumption_until_now"], "3.000")
        self.assertEqual(payload["actual_consumption_until_now"], "3.000")
        self.assertEqual(payload["divergence"], "0.000")
        self.assertEqual(payload["status"], "low_stock")
        self.assertTrue(payload["should_alert"])

    def test_patient_consumption_summary_exposes_dose_schedule_snapshot_for_scheduled_items(self):
        self._set_fixed_scheduled_context(
            specific_times=["08:00", "20:00"],
            frequency_per_day=2,
            actual_consumption="1",
            current_stock="120",
            administration_times=["08:05"],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/patients/{self.patient_id}/consumption-summary",
                    params={"reference_date": "2026-04-10"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total_items"], 1)
        item = payload["items"][0]
        self.assertEqual(item["administration_day_status"], "partially_completed_day")
        self.assertEqual(
            item["dose_schedule"],
            {
                "total_doses": 2,
                "completed_dose_count": 1,
                "due_now_dose_count": 0,
                "overdue_dose_count": 0,
                "not_due_yet_dose_count": 1,
                "next_dose": {
                    "scheduled_at": "2026-04-10T20:00:00Z",
                    "tolerated_until": "2026-04-10T20:30:00Z",
                    "dose_amount": "1.000",
                    "state": "not_due_yet",
                    "prescription_id": str(
                        self.prescriptions_map[(self.patient_id, self.item_id)][0].id
                    ),
                    "matched_occurred_at": None,
                },
                "overdue_dose": None,
            },
        )

    def test_patient_dose_schedule_endpoint_lists_daily_doses_and_next_overdue_views(self):
        self._set_fixed_scheduled_context(
            specific_times=["08:00", "12:00", "20:00"],
            frequency_per_day=3,
            actual_consumption="1",
            current_stock="120",
            administration_times=["08:05"],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 15, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/patients/{self.patient_id}/dose-schedule",
                    params={"reference_date": "2026-04-10"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["patient_id"], str(self.patient_id))
        self.assertEqual(payload["total_doses"], 3)
        self.assertEqual(payload["completed_dose_count"], 1)
        self.assertEqual(payload["due_now_dose_count"], 0)
        self.assertEqual(payload["overdue_dose_count"], 1)
        self.assertEqual(payload["not_due_yet_dose_count"], 1)
        self.assertEqual(
            [dose["state"] for dose in payload["doses"]],
            ["completed", "overdue", "not_due_yet"],
        )
        self.assertEqual(payload["next_dose"]["scheduled_at"], "2026-04-10T20:00:00Z")
        self.assertEqual(len(payload["overdue_doses"]), 1)
        self.assertEqual(payload["overdue_doses"][0]["scheduled_at"], "2026-04-10T12:00:00Z")

    def test_alert_candidates_and_sync_flow_connects_calculation_to_internal_alerts_without_duplicate(self):
        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
            patch(
                "app.modules.internal_alerts.services.list_open_alerts_by_type",
                side_effect=self._fake_list_open_alerts_by_type,
            ),
            patch(
                "app.modules.internal_alerts.services.get_item_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.get_patient_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.find_equivalent_open_alert",
                side_effect=self._fake_find_equivalent_open_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
                side_effect=self._fake_update_alert_content,
            ),
            patch(
                "app.modules.internal_alerts.services.resolve_alert",
                side_effect=self._fake_resolve_alert,
            ),
            patch(
                "app.modules.internal_alerts.routes.list_alerts",
                side_effect=self._fake_list_alerts,
            ),
        ):
            with TestClient(app) as client:
                candidates_response = client.get(
                    "/calculations/alerts-candidates",
                    params={"reference_date": "2026-04-08"},
                )
                first_sync_response = client.post(
                    "/calculations/alerts-sync",
                    params={"reference_date": "2026-04-08"},
                )
                second_sync_response = client.post(
                    "/calculations/alerts-sync",
                    params={"reference_date": "2026-04-08"},
                )

                self.stock_map[self.item_id] = Decimal("120")
                self.actual_map[(self.patient_id, self.item_id)] = Decimal("3")

                third_sync_response = client.post(
                    "/calculations/alerts-sync",
                    params={"reference_date": "2026-04-08"},
                )
                open_alerts_response = client.get(
                    "/alerts",
                    params={"status": "open"},
                )

        self.assertEqual(candidates_response.status_code, 200)
        candidates_payload = candidates_response.json()
        self.assertEqual(candidates_payload["total"], 1)
        self.assertEqual(candidates_payload["data"][0]["status"], "low_stock")

        self.assertEqual(first_sync_response.status_code, 200)
        self.assertEqual(
            first_sync_response.json()["data"],
            {
                "reference_date": "2026-04-08",
                "candidate_total": 1,
                "created": 1,
                "updated": 0,
                "resolved": 0,
                "unchanged": 0,
            },
        )

        self.assertEqual(second_sync_response.status_code, 200)
        self.assertEqual(
            second_sync_response.json()["data"]["unchanged"],
            1,
        )

        self.assertEqual(third_sync_response.status_code, 200)
        self.assertEqual(
            third_sync_response.json()["data"],
            {
                "reference_date": "2026-04-08",
                "candidate_total": 0,
                "created": 0,
                "updated": 0,
                "resolved": 1,
                "unchanged": 0,
            },
        )

        self.assertEqual(open_alerts_response.status_code, 200)
        open_payload = open_alerts_response.json()
        self.assertEqual(open_payload["total"], 0)

    def test_fixed_scheduled_future_dose_is_not_charged_or_alerted(self):
        self.alerts_store = []
        self._set_fixed_scheduled_context(
            specific_times=["08:00", "20:00"],
            frequency_per_day=2,
            actual_consumption="1",
            current_stock="120",
            administration_times=["08:05"],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
            patch(
                "app.modules.internal_alerts.services.list_open_alerts_by_type",
                side_effect=self._fake_list_open_alerts_by_type,
            ),
            patch(
                "app.modules.internal_alerts.services.get_item_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.get_patient_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.find_equivalent_open_alert",
                side_effect=self._fake_find_equivalent_open_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
                side_effect=self._fake_update_alert_content,
            ),
            patch(
                "app.modules.internal_alerts.services.resolve_alert",
                side_effect=self._fake_resolve_alert,
            ),
            patch(
                "app.modules.internal_alerts.routes.list_alerts",
                side_effect=self._fake_list_alerts,
            ),
        ):
            with TestClient(app) as client:
                projection_response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-10"},
                )
                candidates_response = client.get(
                    "/calculations/alerts-candidates",
                    params={"reference_date": "2026-04-10"},
                )
                sync_response = client.post(
                    "/calculations/alerts-sync",
                    params={"reference_date": "2026-04-10"},
                )
                alerts_response = client.get("/alerts", params={"status": "open"})

        self.assertEqual(projection_response.status_code, 200)
        projection_payload = projection_response.json()["data"]
        self.assertEqual(projection_payload["comparison_window"], "scheduled_times")
        self.assertEqual(projection_payload["expected_consumption_until_now"], "1.000")
        self.assertEqual(projection_payload["actual_consumption_until_now"], "1.000")
        self.assertEqual(
            projection_payload["administration_day_status"],
            "partially_completed_day",
        )
        self.assertEqual(
            [occurrence["state"] for occurrence in projection_payload["dose_occurrences"]],
            ["completed", "not_due_yet"],
        )
        self.assertEqual(projection_payload["status"], "ok")
        self.assertFalse(projection_payload["should_alert"])

        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual(candidates_response.json()["total"], 0)

        self.assertEqual(sync_response.status_code, 200)
        self.assertEqual(
            sync_response.json()["data"],
            {
                "reference_date": "2026-04-10",
                "candidate_total": 0,
                "created": 0,
                "updated": 0,
                "resolved": 0,
                "unchanged": 0,
            },
        )

        self.assertEqual(alerts_response.status_code, 200)
        self.assertEqual(alerts_response.json()["total"], 0)

    def test_fixed_scheduled_delay_generates_divergence_alert_after_due_time(self):
        self.alerts_store = []
        self._set_fixed_scheduled_context(
            specific_times=["08:00", "20:00"],
            frequency_per_day=2,
            actual_consumption="0",
            current_stock="120",
            administration_times=[],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
            patch(
                "app.modules.internal_alerts.services.list_open_alerts_by_type",
                side_effect=self._fake_list_open_alerts_by_type,
            ),
            patch(
                "app.modules.internal_alerts.services.get_item_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.get_patient_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.find_equivalent_open_alert",
                side_effect=self._fake_find_equivalent_open_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
                side_effect=self._fake_update_alert_content,
            ),
            patch(
                "app.modules.internal_alerts.services.resolve_alert",
                side_effect=self._fake_resolve_alert,
            ),
            patch(
                "app.modules.internal_alerts.routes.list_alerts",
                side_effect=self._fake_list_alerts,
            ),
        ):
            with TestClient(app) as client:
                projection_response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-10"},
                )
                candidates_response = client.get(
                    "/calculations/alerts-candidates",
                    params={"reference_date": "2026-04-10"},
                )
                sync_response = client.post(
                    "/calculations/alerts-sync",
                    params={"reference_date": "2026-04-10"},
                )
                alerts_response = client.get("/alerts", params={"status": "open"})

        self.assertEqual(projection_response.status_code, 200)
        projection_payload = projection_response.json()["data"]
        self.assertEqual(projection_payload["comparison_window"], "scheduled_times")
        self.assertEqual(projection_payload["expected_consumption_until_now"], "1.000")
        self.assertEqual(projection_payload["actual_consumption_until_now"], "0.000")
        self.assertEqual(
            projection_payload["administration_day_status"],
            "missed_dose",
        )
        self.assertEqual(
            [occurrence["state"] for occurrence in projection_payload["dose_occurrences"]],
            ["overdue", "not_due_yet"],
        )
        self.assertEqual(projection_payload["status"], "consumption_below_expected")
        self.assertTrue(projection_payload["should_alert"])
        self.assertEqual(
            projection_payload["alert_reason"],
            "Existe dose atrasada sem registro de administracao apos a tolerancia configurada.",
        )

        self.assertEqual(candidates_response.status_code, 200)
        candidates_payload = candidates_response.json()
        self.assertEqual(candidates_payload["total"], 1)
        self.assertEqual(
            candidates_payload["data"][0]["status"],
            "consumption_below_expected",
        )

        self.assertEqual(sync_response.status_code, 200)
        self.assertEqual(sync_response.json()["data"]["candidate_total"], 1)
        self.assertEqual(sync_response.json()["data"]["created"], 1)

        self.assertEqual(alerts_response.status_code, 200)
        alerts_payload = alerts_response.json()
        self.assertEqual(alerts_payload["total"], 1)
        alert = alerts_payload["data"][0]
        self.assertEqual(alert["status"], "open")
        self.assertEqual(alert["severity"], "warning")
        self.assertEqual(alert["title"], "Dose atrasada de Dipirona 500mg")
        self.assertEqual(
            alert["reason"],
            "Existe dose atrasada sem registro de administracao apos a tolerancia configurada.",
        )
        self.assertIn(
            "Horario(s) em atraso: 08:00.",
            alert["message"],
        )

    def test_fixed_scheduled_dose_inside_tolerance_does_not_alert_yet(self):
        self.alerts_store = []
        self._set_fixed_scheduled_context(
            specific_times=["20:00"],
            frequency_per_day=1,
            actual_consumption="0",
            current_stock="120",
            administration_times=[],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 20, 10, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
            patch(
                "app.modules.internal_alerts.services.list_open_alerts_by_type",
                side_effect=self._fake_list_open_alerts_by_type,
            ),
            patch(
                "app.modules.internal_alerts.services.get_item_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.get_patient_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.find_equivalent_open_alert",
                side_effect=self._fake_find_equivalent_open_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
                side_effect=self._fake_update_alert_content,
            ),
            patch(
                "app.modules.internal_alerts.services.resolve_alert",
                side_effect=self._fake_resolve_alert,
            ),
            patch(
                "app.modules.internal_alerts.routes.list_alerts",
                side_effect=self._fake_list_alerts,
            ),
        ):
            with TestClient(app) as client:
                projection_response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-10"},
                )
                candidates_response = client.get(
                    "/calculations/alerts-candidates",
                    params={"reference_date": "2026-04-10"},
                )
                sync_response = client.post(
                    "/calculations/alerts-sync",
                    params={"reference_date": "2026-04-10"},
                )
                alerts_response = client.get("/alerts", params={"status": "open"})

        self.assertEqual(projection_response.status_code, 200)
        projection_payload = projection_response.json()["data"]
        self.assertEqual(projection_payload["expected_consumption_until_now"], "0.000")
        self.assertEqual(projection_payload["actual_consumption_until_now"], "0.000")
        self.assertEqual(projection_payload["administration_day_status"], "due_now")
        self.assertEqual(
            [occurrence["state"] for occurrence in projection_payload["dose_occurrences"]],
            ["due_now"],
        )
        self.assertEqual(projection_payload["status"], "ok")
        self.assertFalse(projection_payload["should_alert"])

        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual(candidates_response.json()["total"], 0)
        self.assertEqual(sync_response.status_code, 200)
        self.assertEqual(
            sync_response.json()["data"],
            {
                "reference_date": "2026-04-10",
                "candidate_total": 0,
                "created": 0,
                "updated": 0,
                "resolved": 0,
                "unchanged": 0,
            },
        )
        self.assertEqual(alerts_response.status_code, 200)
        self.assertEqual(alerts_response.json()["total"], 0)

    def test_fixed_scheduled_same_day_creation_does_not_charge_past_dose_before_creation(self):
        self.alerts_store = []
        self._set_fixed_scheduled_context(
            specific_times=["08:00", "20:00"],
            frequency_per_day=2,
            actual_consumption="0",
            current_stock="120",
            administration_timestamps=[],
            created_at_value=datetime(2026, 4, 10, 9, 30, tzinfo=timezone.utc),
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
            patch(
                "app.modules.internal_alerts.services.list_open_alerts_by_type",
                side_effect=self._fake_list_open_alerts_by_type,
            ),
            patch(
                "app.modules.internal_alerts.services.get_item_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.get_patient_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.find_equivalent_open_alert",
                side_effect=self._fake_find_equivalent_open_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
                side_effect=self._fake_update_alert_content,
            ),
            patch(
                "app.modules.internal_alerts.routes.list_alerts",
                side_effect=self._fake_list_alerts,
            ),
        ):
            with TestClient(app) as client:
                projection_response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-10"},
                )
                candidates_response = client.get(
                    "/calculations/alerts-candidates",
                    params={"reference_date": "2026-04-10"},
                )

        self.assertEqual(projection_response.status_code, 200)
        projection_payload = projection_response.json()["data"]
        self.assertEqual(projection_payload["expected_consumption_until_now"], "0.000")
        self.assertEqual(projection_payload["actual_consumption_until_now"], "0.000")
        self.assertEqual(projection_payload["administration_day_status"], "not_due_yet")
        self.assertEqual(
            [occurrence["state"] for occurrence in projection_payload["dose_occurrences"]],
            ["not_due_yet"],
        )
        self.assertEqual(projection_payload["status"], "ok")
        self.assertFalse(projection_payload["should_alert"])

        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual(candidates_response.json()["total"], 0)

    def test_fixed_scheduled_creation_after_last_dose_of_the_day_does_not_alert(self):
        self.alerts_store = []
        self._set_fixed_scheduled_context(
            specific_times=["08:00", "20:00"],
            frequency_per_day=2,
            actual_consumption="0",
            current_stock="120",
            administration_timestamps=[],
            created_at_value=datetime(2026, 4, 10, 21, 53, tzinfo=timezone.utc),
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 22, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
        ):
            with TestClient(app) as client:
                projection_response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-10"},
                )
                candidates_response = client.get(
                    "/calculations/alerts-candidates",
                    params={"reference_date": "2026-04-10"},
                )

        self.assertEqual(projection_response.status_code, 200)
        projection_payload = projection_response.json()["data"]
        self.assertEqual(projection_payload["expected_consumption_until_now"], "0.000")
        self.assertEqual(projection_payload["actual_consumption_until_now"], "0.000")
        self.assertEqual(projection_payload["administration_day_status"], "not_due_yet")
        self.assertEqual(projection_payload["dose_occurrences"], [])
        self.assertEqual(projection_payload["status"], "ok")
        self.assertFalse(projection_payload["should_alert"])

        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual(candidates_response.json()["total"], 0)

    def test_fixed_scheduled_dose_after_tolerance_generates_alert(self):
        self.alerts_store = []
        self._set_fixed_scheduled_context(
            specific_times=["20:00"],
            frequency_per_day=1,
            actual_consumption="0",
            current_stock="120",
            administration_times=[],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 20, 35, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
            patch(
                "app.modules.internal_alerts.services.list_open_alerts_by_type",
                side_effect=self._fake_list_open_alerts_by_type,
            ),
            patch(
                "app.modules.internal_alerts.services.get_item_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.get_patient_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.find_equivalent_open_alert",
                side_effect=self._fake_find_equivalent_open_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
                side_effect=self._fake_update_alert_content,
            ),
            patch(
                "app.modules.internal_alerts.routes.list_alerts",
                side_effect=self._fake_list_alerts,
            ),
        ):
            with TestClient(app) as client:
                projection_response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-10"},
                )
                candidates_response = client.get(
                    "/calculations/alerts-candidates",
                    params={"reference_date": "2026-04-10"},
                )

        self.assertEqual(projection_response.status_code, 200)
        projection_payload = projection_response.json()["data"]
        self.assertEqual(projection_payload["expected_consumption_until_now"], "1.000")
        self.assertEqual(projection_payload["actual_consumption_until_now"], "0.000")
        self.assertEqual(
            projection_payload["administration_day_status"],
            "missed_dose",
        )
        self.assertEqual(
            [occurrence["state"] for occurrence in projection_payload["dose_occurrences"]],
            ["overdue"],
        )
        self.assertEqual(
            projection_payload["status"],
            "consumption_below_expected",
        )
        self.assertTrue(projection_payload["should_alert"])

        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual(candidates_response.json()["total"], 1)

    def test_fixed_scheduled_late_record_marks_the_dose_as_completed_and_clears_candidates(self):
        self.alerts_store = []
        self._set_fixed_scheduled_context(
            specific_times=["08:00"],
            frequency_per_day=1,
            actual_consumption="0",
            current_stock="120",
            administration_timestamps=[],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
            patch(
                "app.modules.internal_alerts.services.list_open_alerts_by_type",
                side_effect=self._fake_list_open_alerts_by_type,
            ),
            patch(
                "app.modules.internal_alerts.services.get_item_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.get_patient_for_alert_or_raise",
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.find_equivalent_open_alert",
                side_effect=self._fake_find_equivalent_open_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
                side_effect=self._fake_update_alert_content,
            ),
            patch(
                "app.modules.internal_alerts.services.resolve_alert",
                side_effect=self._fake_resolve_alert,
            ),
            patch(
                "app.modules.internal_alerts.routes.list_alerts",
                side_effect=self._fake_list_alerts,
            ),
        ):
            with TestClient(app) as client:
                first_sync_response = client.post(
                    "/calculations/alerts-sync",
                    params={"reference_date": "2026-04-10"},
                )

                self.actual_map[(self.patient_id, self.item_id)] = Decimal("1")
                self.administration_records_map[(self.patient_id, self.item_id)] = [
                    DoseAdministrationRecord(
                        occurred_at=datetime(2026, 4, 10, 9, 45, tzinfo=timezone.utc),
                        quantity=Decimal("1"),
                        prescription_id=self.prescriptions_map[(self.patient_id, self.item_id)][0].id,
                    )
                ]

                projection_response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-10"},
                )
                candidates_response = client.get(
                    "/calculations/alerts-candidates",
                    params={"reference_date": "2026-04-10"},
                )
                second_sync_response = client.post(
                    "/calculations/alerts-sync",
                    params={"reference_date": "2026-04-10"},
                )
                alerts_response = client.get("/alerts", params={"status": "open"})

        self.assertEqual(first_sync_response.status_code, 200)
        self.assertEqual(first_sync_response.json()["data"]["created"], 1)
        self.assertEqual(projection_response.status_code, 200)
        projection_payload = projection_response.json()["data"]
        self.assertEqual(projection_payload["administration_day_status"], "completed")
        self.assertEqual(
            [occurrence["state"] for occurrence in projection_payload["dose_occurrences"]],
            ["completed"],
        )
        self.assertEqual(projection_payload["status"], "ok")
        self.assertFalse(projection_payload["should_alert"])
        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual(candidates_response.json()["total"], 0)
        self.assertEqual(second_sync_response.status_code, 200)
        self.assertEqual(second_sync_response.json()["data"]["resolved"], 1)
        self.assertEqual(alerts_response.status_code, 200)
        self.assertEqual(alerts_response.json()["total"], 0)

    def test_patient_dose_schedule_endpoint_supports_multiple_medications_in_the_same_day(self):
        self.alerts_store = []
        second_item_id = uuid4()
        self._set_fixed_scheduled_context(
            specific_times=["08:00", "20:00"],
            frequency_per_day=2,
            actual_consumption="1",
            current_stock="120",
            administration_times=["08:05"],
        )
        self._set_fixed_scheduled_context(
            item_id=second_item_id,
            item_name="Amoxicilina 500mg",
            specific_times=["09:00"],
            frequency_per_day=1,
            actual_consumption="0",
            current_stock="80",
            administration_times=[],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
            patch(
                "app.modules.calculation.services._list_active_projection_pairs",
                side_effect=self._fake_list_active_projection_pairs,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/patients/{self.patient_id}/dose-schedule",
                    params={"reference_date": "2026-04-10"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total_doses"], 3)
        self.assertEqual(payload["completed_dose_count"], 1)
        self.assertEqual(payload["overdue_dose_count"], 1)
        self.assertEqual(payload["not_due_yet_dose_count"], 1)
        self.assertEqual(len(payload["doses"]), 3)
        self.assertEqual(
            [dose["item_name"] for dose in payload["doses"]],
            ["Dipirona 500mg", "Amoxicilina 500mg", "Dipirona 500mg"],
        )
        self.assertEqual(payload["next_dose"]["item_name"], "Dipirona 500mg")
        self.assertEqual(payload["overdue_doses"][0]["item_name"], "Amoxicilina 500mg")

    def test_fixed_scheduled_rollover_to_next_day_does_not_reuse_previous_day_administration(self):
        self.alerts_store = []
        self._set_fixed_scheduled_context(
            specific_times=["20:00"],
            frequency_per_day=1,
            actual_consumption="0",
            current_stock="120",
            administration_timestamps=["2026-04-10T20:05:00+00:00"],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.calculation.services.resolve_reference_datetime",
                return_value=datetime(2026, 4, 11, 7, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.modules.calculation.services._get_patient_or_raise",
                side_effect=self._fake_get_patient_or_raise,
            ),
            patch(
                "app.modules.calculation.services._get_item_or_raise",
                side_effect=self._fake_get_item_or_raise,
            ),
            patch(
                "app.modules.calculation.services._list_active_prescriptions_for_patient_item",
                side_effect=self._fake_list_active_prescriptions_for_patient_item,
            ),
            patch(
                "app.modules.calculation.services._calculate_actual_consumption_until_now",
                side_effect=self._fake_calculate_actual_consumption_until_now,
            ),
            patch(
                "app.modules.calculation.services._list_administration_records_until_now",
                side_effect=self._fake_list_administration_records_until_now,
            ),
            patch(
                "app.modules.calculation.services.calculate_current_stock_for_item",
                side_effect=self._fake_calculate_current_stock_for_item,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(
                    f"/patients/{self.patient_id}/items/{self.item_id}/projection",
                    params={"reference_date": "2026-04-11"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["expected_consumption_until_now"], "0.000")
        self.assertEqual(payload["actual_consumption_until_now"], "0.000")
        self.assertEqual(payload["administration_day_status"], "not_due_yet")
        self.assertEqual(
            [occurrence["state"] for occurrence in payload["dose_occurrences"]],
            ["not_due_yet"],
        )


if __name__ == "__main__":
    unittest.main()
