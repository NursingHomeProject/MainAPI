from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.modules.internal_alerts.models import AlertSeverity, AlertStatus

CALCULATION_ALERT_TYPE = "calculation_projection"


class AlertSource(str, Enum):
    MANUAL = "manual"
    CALCULATION_ENGINE = "calculation_engine"


class InternalAlertTrigger(str, Enum):
    LOW_STOCK = "low_stock"
    CRITICAL_STOCK = "critical_stock"
    CONSUMPTION_ABOVE_EXPECTED = "consumption_above_expected"
    CONSUMPTION_BELOW_EXPECTED = "consumption_below_expected"
    INCONSISTENT_DATA = "inconsistent_data"
    INVALID_PRESCRIPTION = "invalid_prescription"


@dataclass(frozen=True)
class InternalAlertContract:
    trigger: InternalAlertTrigger
    severity: AlertSeverity
    default_status: AlertStatus
    source: AlertSource
    title_template: str
    reason_template: str


@dataclass(frozen=True)
class RenderedInternalAlertContract:
    alert_type: str
    trigger: InternalAlertTrigger
    source: AlertSource
    severity: AlertSeverity
    status: AlertStatus
    title: str
    reason: str
    message: str


# Decision table for the MVP:
# - critical_stock / inconsistent_data / invalid_prescription -> critical severity
# - low_stock / consumption_above_expected / consumption_below_expected -> warning severity
# - all auto-generated calculation alerts start as open
INTERNAL_ALERT_CONTRACTS: dict[InternalAlertTrigger, InternalAlertContract] = {
    InternalAlertTrigger.LOW_STOCK: InternalAlertContract(
        trigger=InternalAlertTrigger.LOW_STOCK,
        severity=AlertSeverity.WARNING,
        default_status=AlertStatus.OPEN,
        source=AlertSource.CALCULATION_ENGINE,
        title_template="Estoque baixo de {item_name}",
        reason_template="Saldo em faixa de atencao para reposicao.",
    ),
    InternalAlertTrigger.CRITICAL_STOCK: InternalAlertContract(
        trigger=InternalAlertTrigger.CRITICAL_STOCK,
        severity=AlertSeverity.CRITICAL,
        default_status=AlertStatus.OPEN,
        source=AlertSource.CALCULATION_ENGINE,
        title_template="Estoque critico de {item_name}",
        reason_template="Saldo em faixa critica para operacao.",
    ),
    InternalAlertTrigger.CONSUMPTION_ABOVE_EXPECTED: InternalAlertContract(
        trigger=InternalAlertTrigger.CONSUMPTION_ABOVE_EXPECTED,
        severity=AlertSeverity.WARNING,
        default_status=AlertStatus.OPEN,
        source=AlertSource.CALCULATION_ENGINE,
        title_template="Consumo acima do esperado",
        reason_template="Consumo acima do esperado.",
    ),
    InternalAlertTrigger.CONSUMPTION_BELOW_EXPECTED: InternalAlertContract(
        trigger=InternalAlertTrigger.CONSUMPTION_BELOW_EXPECTED,
        severity=AlertSeverity.WARNING,
        default_status=AlertStatus.OPEN,
        source=AlertSource.CALCULATION_ENGINE,
        title_template="Consumo abaixo do esperado",
        reason_template="Consumo abaixo do esperado.",
    ),
    InternalAlertTrigger.INCONSISTENT_DATA: InternalAlertContract(
        trigger=InternalAlertTrigger.INCONSISTENT_DATA,
        severity=AlertSeverity.CRITICAL,
        default_status=AlertStatus.OPEN,
        source=AlertSource.CALCULATION_ENGINE,
        title_template="Dados inconsistentes para acompanhamento",
        reason_template="Os dados atuais do item estao inconsistentes para classificacao operacional.",
    ),
    InternalAlertTrigger.INVALID_PRESCRIPTION: InternalAlertContract(
        trigger=InternalAlertTrigger.INVALID_PRESCRIPTION,
        severity=AlertSeverity.CRITICAL,
        default_status=AlertStatus.OPEN,
        source=AlertSource.CALCULATION_ENGINE,
        title_template="Prescricao invalida para calculo",
        reason_template="Nao foi possivel validar a prescricao ativa para calcular o consumo previsto.",
    ),
}


def get_internal_alert_contract(trigger: InternalAlertTrigger) -> InternalAlertContract:
    return INTERNAL_ALERT_CONTRACTS[trigger]


def try_get_trigger_from_status(status: str | Enum) -> InternalAlertTrigger | None:
    normalized_value = status.value if isinstance(status, Enum) else status
    try:
        return InternalAlertTrigger(str(normalized_value))
    except ValueError:
        return None


def get_alert_source(alert_type: str) -> AlertSource:
    if alert_type == CALCULATION_ALERT_TYPE:
        return AlertSource.CALCULATION_ENGINE
    return AlertSource.MANUAL


def build_calculation_alert_contract(
    trigger: InternalAlertTrigger,
    *,
    item_name: str,
    patient_name: str,
    daily_consumption: str,
    unit_symbol: str,
    reason_override: str | None = None,
) -> RenderedInternalAlertContract:
    contract = get_internal_alert_contract(trigger)
    reason = reason_override or contract.reason_template
    title = contract.title_template.format(item_name=item_name)
    message = (
        f"{reason} Paciente: {patient_name}. "
        f"Item: {item_name}. "
        f"Consumo diario previsto: {daily_consumption} {unit_symbol}."
    )

    return RenderedInternalAlertContract(
        alert_type=CALCULATION_ALERT_TYPE,
        trigger=trigger,
        source=contract.source,
        severity=contract.severity,
        status=contract.default_status,
        title=title,
        reason=reason,
        message=message,
    )
