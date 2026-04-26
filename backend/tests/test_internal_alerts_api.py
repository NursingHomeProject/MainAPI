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
from app.modules.calculation.schemas import (
    CalculationAdministrationDayStatus,
    CalculationDivergenceStatus,
    CalculationDoseOccurrence,
    CalculationDoseOccurrenceState,
    CalculationEnginePayload,
    CalculationOperationalStatus,
)
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)
from app.modules.internal_alerts.models import AlertSeverity, AlertStatus
from app.modules.internal_alerts.schemas import CALCULATION_ALERT_TYPE, AlertCreate
from app.modules.internal_alerts.schemas import AlertSummaryResponse
from app.modules.internal_alerts.services import (
    AlertResolutionAction,
    AlertResolutionResult,
    AlertUpsertResult,
    build_alert_summary,
    create_alert_from_calculation_projection,
    create_or_reuse_alert,
    summarize_alerts,
)


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, statement):
        return _FakeExecuteResult(self._rows)


class InternalAlertsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sentinel_db = object()
        self.fake_user = SimpleNamespace(id=uuid4(), is_active=True)
        self.patient_id = uuid4()
        self.item_id = uuid4()
        self.now = datetime.now(timezone.utc)

        self.alerts_store = [
            SimpleNamespace(
                id=uuid4(),
                item_id=self.item_id,
                patient_id=self.patient_id,
                resolved_by_user_id=None,
                alert_type=CALCULATION_ALERT_TYPE,
                title="Estoque critico de Dipirona 500mg",
                reason="Saldo em faixa critica para operacao.",
                message="Saldo em faixa critica para operacao.",
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.OPEN,
                resolved_at=None,
                created_at=self.now,
                updated_at=self.now,
            ),
            SimpleNamespace(
                id=uuid4(),
                item_id=None,
                patient_id=None,
                resolved_by_user_id=None,
                alert_type="manual_follow_up",
                title="Acompanhar entrega",
                reason="Contato com a familia pendente.",
                message="Contato com a familia pendente.",
                severity=AlertSeverity.WARNING,
                status=AlertStatus.OPEN,
                resolved_at=None,
                created_at=self.now,
                updated_at=self.now,
            ),
            SimpleNamespace(
                id=uuid4(),
                item_id=self.item_id,
                patient_id=self.patient_id,
                resolved_by_user_id=self.fake_user.id,
                alert_type="manual_follow_up",
                title="Entrega confirmada",
                reason="Fluxo concluido.",
                message="Fluxo concluido.",
                severity=AlertSeverity.INFO,
                status=AlertStatus.RESOLVED,
                resolved_at=self.now,
                created_at=self.now,
                updated_at=self.now,
            ),
        ]

        app.dependency_overrides[get_db] = self._override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: self.fake_user

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _override_get_db(self):
        yield self.sentinel_db

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

    def _fake_get_alert_by_id(self, db, alert_id):
        for alert in self.alerts_store:
            if alert.id == alert_id:
                return alert
        return None

    def _fake_resolve_alert(self, db, alert, *, resolved_by_user_id=None):
        alert.status = AlertStatus.RESOLVED
        alert.resolved_by_user_id = resolved_by_user_id
        alert.resolved_at = datetime.now(timezone.utc)
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

    def _fake_resolve_alert_manually(self, db, alert, *, resolved_by_user_id=None):
        if alert.status == AlertStatus.RESOLVED:
            return AlertResolutionResult(
                alert=alert,
                action=AlertResolutionAction.ALREADY_RESOLVED,
                changed=False,
            )

        resolved_alert = self._fake_resolve_alert(
            db,
            alert,
            resolved_by_user_id=resolved_by_user_id,
        )
        return AlertResolutionResult(
            alert=resolved_alert,
            action=AlertResolutionAction.RESOLVED,
            changed=True,
        )

    def _build_projection(
        self,
        *,
        status: CalculationOperationalStatus,
        should_alert: bool,
        alert_reason: str | None,
        administration_day_status: CalculationAdministrationDayStatus | None = None,
        administration_day_reason: str | None = None,
        dose_occurrences: list[CalculationDoseOccurrence] | None = None,
        current_stock: str = "12.000",
        days_remaining: str | None = "4.00",
        divergence: str | None = None,
        divergence_status: CalculationDivergenceStatus = CalculationDivergenceStatus.COHERENT,
        actual_consumption_until_now: str | None = "12.000",
        expected_consumption_until_now: str | None = "12.000",
    ) -> CalculationEnginePayload:
        return CalculationEnginePayload(
            reference_date=date(2026, 4, 10),
            patient_id=self.patient_id,
            patient_name="Paciente Fernando",
            item_id=self.item_id,
            item_name="Dipirona 500mg",
            unit_symbol="comprimido",
            usage_mode=PrescriptionUsageMode.FIXED,
            comparison_window=PrescriptionComparisonWindow.DAILY_TOTAL,
            daily_consumption=Decimal("3.000"),
            current_stock=Decimal(current_stock),
            days_remaining=Decimal(days_remaining) if days_remaining is not None else None,
            expected_consumption_until_now=(
                Decimal(expected_consumption_until_now)
                if expected_consumption_until_now is not None
                else None
            ),
            actual_consumption_until_now=(
                Decimal(actual_consumption_until_now)
                if actual_consumption_until_now is not None
                else None
            ),
            divergence=Decimal(divergence) if divergence is not None else None,
            divergence_status=divergence_status,
            administration_day_status=administration_day_status,
            administration_day_reason=administration_day_reason,
            dose_occurrences=dose_occurrences,
            status=status,
            should_alert=should_alert,
            alert_reason=alert_reason,
            is_valid=True,
            invalid_reason=None,
        )

    def test_alerts_list_supports_filters_and_exposes_traceability_fields(self):
        with patch(
            "app.modules.internal_alerts.routes.list_alerts",
            side_effect=self._fake_list_alerts,
        ):
            with TestClient(app) as client:
                response = client.get(
                    "/alerts",
                    params={
                        "status": "open",
                        "alert_type": CALCULATION_ALERT_TYPE,
                        "patient_id": str(self.patient_id),
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        alert = payload["data"][0]
        self.assertEqual(alert["alert_type"], CALCULATION_ALERT_TYPE)
        self.assertEqual(alert["reason"], "Saldo em faixa critica para operacao.")
        self.assertEqual(alert["severity"], "critical")
        self.assertTrue(alert["is_calculation_generated"])
        self.assertEqual(alert["source"], "calculation_engine")
        self.assertEqual(payload["summary"]["open_total"], 1)
        self.assertEqual(payload["summary"]["open_critical"], 1)
        self.assertEqual(payload["summary"]["patients_with_open_alerts"], 1)
        self.assertEqual(payload["summary"]["items_with_open_alerts"], 1)

    def test_alerts_resolve_route_keeps_manual_resolution(self):
        alert = self.alerts_store[0]

        with (
            patch(
                "app.modules.internal_alerts.routes.get_alert_by_id",
                side_effect=self._fake_get_alert_by_id,
            ),
            patch(
                "app.modules.internal_alerts.routes.resolve_alert_manually",
                side_effect=self._fake_resolve_alert_manually,
            ),
        ):
            with TestClient(app) as client:
                response = client.post(f"/alerts/{alert.id}/resolve")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        payload = body["data"]
        self.assertEqual(body["action"], "resolved")
        self.assertFalse(body["already_resolved"])
        self.assertEqual(body["message"], "Alerta resolvido com sucesso.")
        self.assertEqual(payload["status"], "resolved")
        self.assertEqual(payload["resolved_by_user_id"], str(self.fake_user.id))
        self.assertIsNotNone(payload["resolved_at"])

    def test_alerts_resolve_route_is_idempotent_for_already_resolved_alert(self):
        alert = self.alerts_store[2]
        original_resolved_at = alert.resolved_at
        original_resolved_by = alert.resolved_by_user_id

        with (
            patch(
                "app.modules.internal_alerts.routes.get_alert_by_id",
                side_effect=self._fake_get_alert_by_id,
            ),
            patch(
                "app.modules.internal_alerts.routes.resolve_alert_manually",
                side_effect=self._fake_resolve_alert_manually,
            ),
        ):
            with TestClient(app) as client:
                response = client.post(f"/alerts/{alert.id}/resolve")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        payload = body["data"]
        self.assertEqual(body["action"], "already_resolved")
        self.assertTrue(body["already_resolved"])
        self.assertEqual(body["message"], "Alerta ja estava resolvido.")
        self.assertEqual(payload["status"], "resolved")
        self.assertEqual(payload["resolved_by_user_id"], str(original_resolved_by))
        self.assertEqual(payload["resolved_at"], original_resolved_at.isoformat().replace("+00:00", "Z"))

    def test_alert_summary_service_counts_by_status_severity_and_source(self):
        alerts = [
            SimpleNamespace(
                status=AlertStatus.OPEN,
                severity=AlertSeverity.CRITICAL,
                alert_type=CALCULATION_ALERT_TYPE,
                reason="Saldo em faixa critica para operacao.",
                patient_id=self.patient_id,
                item_id=self.item_id,
            ),
            SimpleNamespace(
                status=AlertStatus.OPEN,
                severity=AlertSeverity.WARNING,
                alert_type="manual_follow_up",
                reason="Contato com a familia pendente.",
                patient_id=None,
                item_id=None,
            ),
            SimpleNamespace(
                status=AlertStatus.OPEN,
                severity=AlertSeverity.INFO,
                alert_type="manual_follow_up",
                reason="Contato com a familia pendente.",
                patient_id=None,
                item_id=None,
            ),
            SimpleNamespace(
                status=AlertStatus.RESOLVED,
                severity=AlertSeverity.WARNING,
                alert_type=CALCULATION_ALERT_TYPE,
                reason="Saldo em faixa critica para operacao.",
                patient_id=self.patient_id,
                item_id=self.item_id,
            ),
        ]

        summary = summarize_alerts(alerts)

        self.assertEqual(summary.open_total, 3)
        self.assertEqual(summary.resolved_total, 1)
        self.assertEqual(summary.open_critical, 1)
        self.assertEqual(summary.open_warning, 1)
        self.assertEqual(summary.open_info, 1)
        self.assertEqual(summary.calculation_open, 1)
        self.assertEqual(summary.manual_open, 2)
        self.assertEqual(summary.patients_with_open_alerts, 1)
        self.assertEqual(summary.items_with_open_alerts, 1)

    def test_alerts_summary_route_returns_operational_counts(self):
        expected_summary = AlertSummaryResponse(
            open_total=2,
            resolved_total=1,
            open_critical=1,
            open_warning=1,
            open_info=0,
            calculation_open=1,
            manual_open=1,
            patients_with_open_alerts=1,
            items_with_open_alerts=1,
        )

        with patch(
            "app.modules.internal_alerts.routes.build_alert_summary",
            return_value=expected_summary,
        ):
            with TestClient(app) as client:
                response = client.get(
                    "/alerts/summary",
                    params={
                        "patient_id": str(self.patient_id),
                        "status": "open",
                        "severity": "critical",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], expected_summary.model_dump())

    def test_alert_summary_service_supports_filters(self):
        with patch(
            "app.modules.internal_alerts.services.list_alerts",
            return_value=[
                SimpleNamespace(
                    status=AlertStatus.OPEN,
                    severity=AlertSeverity.CRITICAL,
                    alert_type=CALCULATION_ALERT_TYPE,
                    reason="Saldo em faixa critica para operacao.",
                    patient_id=self.patient_id,
                    item_id=self.item_id,
                ),
                SimpleNamespace(
                    status=AlertStatus.OPEN,
                    severity=AlertSeverity.WARNING,
                    alert_type="manual_follow_up",
                    reason="Contato com a familia pendente.",
                    patient_id=None,
                    item_id=None,
                ),
            ],
        ) as list_alerts_mock:
            summary = build_alert_summary(
                self.sentinel_db,
                status_filter=AlertStatus.OPEN,
                severity_filter=AlertSeverity.CRITICAL,
                patient_id=self.patient_id,
            )

        self.assertEqual(summary.open_total, 2)
        self.assertEqual(summary.patients_with_open_alerts, 1)
        list_alerts_mock.assert_called_once_with(
            self.sentinel_db,
            status_filter=AlertStatus.OPEN,
            severity_filter=AlertSeverity.CRITICAL,
            alert_type_filter=None,
            patient_id=self.patient_id,
            item_id=None,
        )

    def test_create_or_reuse_alert_avoids_duplicate_open_alert(self):
        existing_alert = self.alerts_store[0]
        payload = AlertCreate(
            alert_type=CALCULATION_ALERT_TYPE,
            title=existing_alert.title,
            reason=existing_alert.reason,
            message=existing_alert.message,
            severity=existing_alert.severity,
            patient_id=existing_alert.patient_id,
            item_id=existing_alert.item_id,
        )

        with (
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
                return_value=existing_alert,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
            ) as create_alert_mock,
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
            ) as update_alert_mock,
        ):
            result = create_or_reuse_alert(self.sentinel_db, payload)

        self.assertIsInstance(result, AlertUpsertResult)
        self.assertFalse(result.created)
        self.assertFalse(result.updated)
        self.assertEqual(result.alert.id, existing_alert.id)
        create_alert_mock.assert_not_called()
        update_alert_mock.assert_not_called()

    def test_create_or_reuse_alert_derives_reason_from_message_when_missing(self):
        payload = AlertCreate(
            alert_type="manual_follow_up",
            title="Acompanhar entrega",
            message="Contato com a familia pendente. Retorno aguardado.",
            severity=AlertSeverity.WARNING,
            patient_id=self.patient_id,
            item_id=self.item_id,
        )

        with (
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
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
        ):
            result = create_or_reuse_alert(self.sentinel_db, payload)

        self.assertTrue(result.created)
        self.assertEqual(result.alert.reason, "Contato com a familia pendente.")

    def test_create_alert_route_reuses_equivalent_open_alert(self):
        existing_alert = self.alerts_store[0]
        upsert_result = AlertUpsertResult(
            alert=existing_alert,
            created=False,
            updated=False,
        )

        with patch(
            "app.modules.internal_alerts.routes.create_or_reuse_alert",
            return_value=upsert_result,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/alerts",
                    json={
                        "alert_type": CALCULATION_ALERT_TYPE,
                        "title": existing_alert.title,
                        "reason": existing_alert.reason,
                        "message": existing_alert.message,
                        "severity": existing_alert.severity.value,
                        "patient_id": str(existing_alert.patient_id),
                        "item_id": str(existing_alert.item_id),
                    },
                )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["data"]
        self.assertEqual(payload["id"], str(existing_alert.id))

    def test_create_alert_from_calculation_projection_creates_low_stock_alert(self):
        self.alerts_store = []
        projection = self._build_projection(
            status=CalculationOperationalStatus.LOW_STOCK,
            should_alert=True,
            alert_reason="Saldo em faixa de atencao para reposicao.",
            current_stock="12.000",
            days_remaining="4.00",
        )

        with (
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
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ) as create_alert_mock,
        ):
            result = create_alert_from_calculation_projection(self.sentinel_db, projection)

        self.assertTrue(result.created)
        self.assertFalse(result.reused)
        self.assertEqual(result.action.value, "created")
        self.assertEqual(result.alert.title, "Estoque baixo de Dipirona 500mg")
        self.assertEqual(result.alert.reason, "Saldo em faixa de atencao para reposicao.")
        self.assertEqual(result.alert.severity, AlertSeverity.WARNING)
        self.assertIn("Saldo atual: 12.000 comprimido.", result.alert.message)
        self.assertIn("Cobertura estimada: 4.00 dia(s).", result.alert.message)
        create_alert_mock.assert_called_once()

    def test_create_alert_from_calculation_projection_reuses_equivalent_divergence_alert(self):
        self.alerts_store = []
        projection = self._build_projection(
            status=CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED,
            should_alert=True,
            alert_reason="Consumo acima do esperado.",
            current_stock="30.000",
            days_remaining="10.00",
            expected_consumption_until_now="24.000",
            actual_consumption_until_now="30.000",
            divergence="6.000",
            divergence_status=CalculationDivergenceStatus.ABOVE_EXPECTED,
        )

        with (
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
            ) as create_alert_mock,
            patch(
                "app.modules.internal_alerts.services.update_alert_content",
                side_effect=self._fake_update_alert_content,
            ) as update_alert_mock,
        ):
            first_result = create_alert_from_calculation_projection(self.sentinel_db, projection)
            second_result = create_alert_from_calculation_projection(self.sentinel_db, projection)

        self.assertTrue(first_result.created)
        self.assertEqual(first_result.alert.title, "Consumo acima do esperado")
        self.assertEqual(first_result.alert.reason, "Consumo acima do esperado.")
        self.assertEqual(first_result.alert.severity, AlertSeverity.WARNING)
        self.assertIn("Divergencia acumulada: 6.000 comprimido.", first_result.alert.message)
        self.assertFalse(second_result.created)
        self.assertTrue(second_result.reused)
        self.assertEqual(second_result.action.value, "reused")
        self.assertEqual(second_result.alert.id, first_result.alert.id)
        create_alert_mock.assert_called_once()
        update_alert_mock.assert_not_called()

    def test_create_alert_from_calculation_projection_uses_missed_dose_context_for_scheduled_delay(self):
        self.alerts_store = []
        projection = self._build_projection(
            status=CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
            should_alert=True,
            alert_reason="Existe dose atrasada sem registro de administracao apos a tolerancia configurada.",
            administration_day_status=CalculationAdministrationDayStatus.MISSED_DOSE,
            administration_day_reason="Existe dose atrasada sem registro de administracao apos a tolerancia configurada.",
            dose_occurrences=[
                CalculationDoseOccurrence(
                    scheduled_at=datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
                    tolerated_until=datetime(2026, 4, 10, 8, 30, tzinfo=timezone.utc),
                    dose_amount=Decimal("1.000"),
                    state=CalculationDoseOccurrenceState.OVERDUE,
                    prescription_id=uuid4(),
                    matched_occurred_at=None,
                ),
                CalculationDoseOccurrence(
                    scheduled_at=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
                    tolerated_until=datetime(2026, 4, 10, 20, 30, tzinfo=timezone.utc),
                    dose_amount=Decimal("1.000"),
                    state=CalculationDoseOccurrenceState.NOT_DUE_YET,
                    prescription_id=uuid4(),
                    matched_occurred_at=None,
                ),
            ],
            current_stock="30.000",
            days_remaining="10.00",
            expected_consumption_until_now="1.000",
            actual_consumption_until_now="0.000",
            divergence="-1.000",
            divergence_status=CalculationDivergenceStatus.BELOW_EXPECTED,
        ).model_copy(
            update={"comparison_window": PrescriptionComparisonWindow.SCHEDULED_TIMES}
        )

        with (
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
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
        ):
            result = create_alert_from_calculation_projection(self.sentinel_db, projection)

        self.assertTrue(result.created)
        self.assertEqual(result.alert.title, "Dose atrasada de Dipirona 500mg")
        self.assertEqual(
            result.alert.reason,
            "Existe dose atrasada sem registro de administracao apos a tolerancia configurada.",
        )
        self.assertIn("Horario(s) em atraso: 08:00.", result.alert.message)

    def test_create_alert_from_calculation_projection_skips_scheduled_divergence_inside_due_window(self):
        projection = self._build_projection(
            status=CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
            should_alert=True,
            alert_reason="Existe dose dentro da janela de administracao e ainda dentro da tolerancia.",
            administration_day_status=CalculationAdministrationDayStatus.DUE_NOW,
            administration_day_reason="Existe dose dentro da janela de administracao e ainda dentro da tolerancia.",
            current_stock="30.000",
            days_remaining="10.00",
            expected_consumption_until_now="1.000",
            actual_consumption_until_now="0.000",
            divergence="-1.000",
            divergence_status=CalculationDivergenceStatus.BELOW_EXPECTED,
        ).model_copy(
            update={"comparison_window": PrescriptionComparisonWindow.SCHEDULED_TIMES}
        )

        with patch(
            "app.modules.internal_alerts.services.create_or_reuse_alert",
        ) as create_or_reuse_mock:
            result = create_alert_from_calculation_projection(self.sentinel_db, projection)

        self.assertIsNone(result.alert)
        self.assertEqual(result.action.value, "skipped")
        self.assertFalse(result.created)
        self.assertFalse(result.reused)
        create_or_reuse_mock.assert_not_called()

    def test_create_alert_from_calculation_projection_uses_info_for_variable_divergence(self):
        self.alerts_store = []
        projection = self._build_projection(
            status=CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
            should_alert=True,
            alert_reason="Uso abaixo da faixa esperada na janela operacional.",
            current_stock="30.000",
            days_remaining="10.00",
            expected_consumption_until_now="3.000",
            actual_consumption_until_now="2.000",
            divergence="-1.000",
            divergence_status=CalculationDivergenceStatus.BELOW_EXPECTED,
        ).model_copy(
            update={
                "usage_mode": PrescriptionUsageMode.VARIABLE,
                "comparison_window": PrescriptionComparisonWindow.ROLLING_24H,
            }
        )

        with (
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
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
        ):
            result = create_alert_from_calculation_projection(self.sentinel_db, projection)

        self.assertTrue(result.created)
        self.assertEqual(result.alert.title, "Uso abaixo da faixa esperada")
        self.assertEqual(
            result.alert.reason,
            "Uso abaixo da faixa esperada na janela operacional.",
        )
        self.assertEqual(result.alert.severity, AlertSeverity.INFO)

    def test_create_alert_from_calculation_projection_skips_when_motor_does_not_signal_alert(self):
        projection = self._build_projection(
            status=CalculationOperationalStatus.OK,
            should_alert=False,
            alert_reason=None,
            current_stock="90.000",
            days_remaining="30.00",
            divergence=None,
        )

        with patch(
            "app.modules.internal_alerts.services.create_or_reuse_alert",
        ) as create_or_reuse_mock:
            result = create_alert_from_calculation_projection(self.sentinel_db, projection)

        self.assertIsNone(result.alert)
        self.assertEqual(result.action.value, "skipped")
        self.assertFalse(result.created)
        self.assertFalse(result.reused)
        create_or_reuse_mock.assert_not_called()

    def test_create_alert_from_calculation_projection_allows_critical_status_even_without_should_alert(self):
        self.alerts_store = []
        projection = self._build_projection(
            status=CalculationOperationalStatus.CRITICAL_STOCK,
            should_alert=False,
            alert_reason="Saldo em faixa critica para operacao.",
            current_stock="0.000",
            days_remaining="0.00",
        )

        with (
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
                return_value=None,
            ),
            patch(
                "app.modules.internal_alerts.services.create_alert",
                side_effect=self._fake_create_alert,
            ),
        ):
            result = create_alert_from_calculation_projection(self.sentinel_db, projection)

        self.assertTrue(result.created)
        self.assertEqual(result.alert.title, "Estoque critico de Dipirona 500mg")
        self.assertEqual(result.alert.reason, "Saldo em faixa critica para operacao.")
        self.assertEqual(result.alert.severity, AlertSeverity.CRITICAL)

    def test_create_alert_from_calculation_projection_skips_on_demand_divergence(self):
        projection = self._build_projection(
            status=CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
            should_alert=True,
            alert_reason="Consumo abaixo do esperado.",
            divergence="-2.000",
            divergence_status=CalculationDivergenceStatus.BELOW_EXPECTED,
        ).model_copy(
            update={"usage_mode": PrescriptionUsageMode.ON_DEMAND}
        )

        with patch(
            "app.modules.internal_alerts.services.create_or_reuse_alert",
        ) as create_or_reuse_mock:
            result = create_alert_from_calculation_projection(self.sentinel_db, projection)

        self.assertIsNone(result.alert)
        self.assertEqual(result.action.value, "skipped")
        self.assertFalse(result.created)
        self.assertFalse(result.reused)
        create_or_reuse_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
