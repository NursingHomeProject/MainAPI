from __future__ import annotations

import unittest

from app.modules.internal_alerts.contracts import (
    AlertSource,
    CALCULATION_ALERT_TYPE,
    INTERNAL_ALERT_CONTRACTS,
    InternalAlertTrigger,
    build_calculation_alert_contract,
    get_alert_source,
    get_internal_alert_contract,
    try_get_trigger_from_status,
)
from app.modules.internal_alerts.models import AlertSeverity, AlertStatus


class InternalAlertContractTests(unittest.TestCase):
    def test_all_mvp_triggers_are_registered(self):
        expected_triggers = {
            InternalAlertTrigger.LOW_STOCK,
            InternalAlertTrigger.CRITICAL_STOCK,
            InternalAlertTrigger.CONSUMPTION_ABOVE_EXPECTED,
            InternalAlertTrigger.CONSUMPTION_BELOW_EXPECTED,
            InternalAlertTrigger.INCONSISTENT_DATA,
            InternalAlertTrigger.INVALID_PRESCRIPTION,
        }
        self.assertEqual(set(INTERNAL_ALERT_CONTRACTS.keys()), expected_triggers)

    def test_decision_table_uses_expected_severity_and_default_status(self):
        self.assertEqual(
            get_internal_alert_contract(InternalAlertTrigger.LOW_STOCK).severity,
            AlertSeverity.WARNING,
        )
        self.assertEqual(
            get_internal_alert_contract(InternalAlertTrigger.CRITICAL_STOCK).severity,
            AlertSeverity.CRITICAL,
        )
        self.assertEqual(
            get_internal_alert_contract(InternalAlertTrigger.CONSUMPTION_ABOVE_EXPECTED).severity,
            AlertSeverity.WARNING,
        )
        self.assertEqual(
            get_internal_alert_contract(InternalAlertTrigger.CONSUMPTION_BELOW_EXPECTED).severity,
            AlertSeverity.WARNING,
        )
        self.assertEqual(
            get_internal_alert_contract(InternalAlertTrigger.INCONSISTENT_DATA).severity,
            AlertSeverity.CRITICAL,
        )
        self.assertEqual(
            get_internal_alert_contract(InternalAlertTrigger.INVALID_PRESCRIPTION).severity,
            AlertSeverity.CRITICAL,
        )

        for trigger in INTERNAL_ALERT_CONTRACTS:
            self.assertEqual(
                get_internal_alert_contract(trigger).default_status,
                AlertStatus.OPEN,
            )

    def test_contract_renders_title_reason_and_message(self):
        rendered = build_calculation_alert_contract(
            InternalAlertTrigger.LOW_STOCK,
            item_name="Dipirona 500mg",
            patient_name="Maria da Conceicao",
            daily_consumption="3.000",
            unit_symbol="comprimido",
        )

        self.assertEqual(rendered.alert_type, CALCULATION_ALERT_TYPE)
        self.assertEqual(rendered.source, AlertSource.CALCULATION_ENGINE)
        self.assertEqual(rendered.severity, AlertSeverity.WARNING)
        self.assertEqual(rendered.status, AlertStatus.OPEN)
        self.assertEqual(rendered.title, "Estoque baixo de Dipirona 500mg")
        self.assertEqual(rendered.reason, "Saldo em faixa de atencao para reposicao.")
        self.assertIn("Paciente: Maria da Conceicao.", rendered.message)
        self.assertIn("Item: Dipirona 500mg.", rendered.message)

    def test_source_and_trigger_helpers_follow_mvp_contract(self):
        self.assertEqual(get_alert_source(CALCULATION_ALERT_TYPE), AlertSource.CALCULATION_ENGINE)
        self.assertEqual(get_alert_source("manual_follow_up"), AlertSource.MANUAL)
        self.assertEqual(
            try_get_trigger_from_status("low_stock"),
            InternalAlertTrigger.LOW_STOCK,
        )
        self.assertIsNone(try_get_trigger_from_status("manual_follow_up"))


if __name__ == "__main__":
    unittest.main()
