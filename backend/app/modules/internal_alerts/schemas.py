from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.modules.internal_alerts.contracts import (
    CALCULATION_ALERT_TYPE,
    AlertSource,
    get_alert_source,
)
from app.modules.internal_alerts.models import AlertSeverity, AlertStatus


class AlertCreate(BaseModel):
    alert_type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=3, max_length=255)
    reason: str | None = Field(default=None, min_length=3, max_length=5000)
    message: str = Field(min_length=3, max_length=5000)
    severity: AlertSeverity = AlertSeverity.WARNING
    item_id: UUID | None = None
    patient_id: UUID | None = None

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, value: str) -> str:
        normalized_value = "_".join(value.strip().lower().split())
        if len(normalized_value) < 2:
            raise ValueError("O tipo do alerta e obrigatorio.")
        return normalized_value

    @field_validator("title", "message", "reason")
    @classmethod
    def validate_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = " ".join(value.split()).strip()
        if len(normalized_value) < 3:
            raise ValueError("O campo informado deve ter pelo menos 3 caracteres.")
        return normalized_value


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID | None
    patient_id: UUID | None
    resolved_by_user_id: UUID | None
    alert_type: str
    title: str
    reason: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @computed_field(return_type=bool)
    @property
    def is_calculation_generated(self) -> bool:
        return self.alert_type == CALCULATION_ALERT_TYPE

    @computed_field(return_type=str)
    @property
    def source(self) -> str:
        return get_alert_source(self.alert_type).value

    @computed_field(return_type=AlertSource)
    @property
    def source_enum(self) -> AlertSource:
        return get_alert_source(self.alert_type)


class AlertDetailEnvelope(BaseModel):
    data: AlertResponse


class AlertListEnvelope(BaseModel):
    data: list[AlertResponse]
    total: int
    summary: AlertSummaryResponse


class AlertSummaryResponse(BaseModel):
    open_total: int
    resolved_total: int
    open_critical: int
    open_warning: int
    open_info: int
    calculation_open: int
    manual_open: int
    patients_with_open_alerts: int
    items_with_open_alerts: int


class AlertSummaryEnvelope(BaseModel):
    data: AlertSummaryResponse


class AlertMessageEnvelope(BaseModel):
    message: str
    action: str | None = None
    already_resolved: bool = False
    data: AlertResponse
