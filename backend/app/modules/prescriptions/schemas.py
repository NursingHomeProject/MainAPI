from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)


class PrescriptionBase(BaseModel):
    patient_id: UUID
    item_id: UUID
    dose_amount: Decimal = Field(gt=0)
    frequency_per_day: int = Field(gt=0)
    specific_times: list[str] | None = None
    usage_mode: PrescriptionUsageMode = PrescriptionUsageMode.FIXED
    comparison_window: PrescriptionComparisonWindow = PrescriptionComparisonWindow.DAILY_TOTAL
    min_expected_per_day: Decimal | None = Field(default=None, ge=0)
    max_expected_per_day: Decimal | None = Field(default=None, ge=0)
    start_date: date
    end_date: date | None = None
    is_active: bool = True

    @field_validator("specific_times")
    @classmethod
    def validate_specific_times(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value

        normalized_times: list[str] = []
        for time_value in value:
            normalized_time = time_value.strip()
            parts = normalized_time.split(":")
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                raise ValueError("Os horarios devem estar no formato HH:MM.")
            hour, minute = int(parts[0]), int(parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError("Os horarios devem estar no formato HH:MM.")
            normalized_times.append(f"{hour:02d}:{minute:02d}")

        if len(set(normalized_times)) != len(normalized_times):
            raise ValueError("Os horarios especificos nao podem se repetir.")

        return normalized_times

    @model_validator(mode="after")
    def validate_dates_and_frequency(self) -> "PrescriptionBase":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("A data final nao pode ser anterior a data inicial.")
        if self.specific_times is not None and len(self.specific_times) != self.frequency_per_day:
            raise ValueError("A quantidade de horarios deve corresponder a frequencia diaria.")
        if (
            self.usage_mode == PrescriptionUsageMode.FIXED
            and self.comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
            and not self.specific_times
        ):
            raise ValueError("Prescricoes fixas com comparacao por horario exigem specific_times.")
        if (
            self.usage_mode != PrescriptionUsageMode.FIXED
            and self.comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
        ):
            raise ValueError("A janela scheduled_times e reservada para prescricoes fixas.")
        if (
            self.min_expected_per_day is not None
            and self.max_expected_per_day is not None
            and self.max_expected_per_day < self.min_expected_per_day
        ):
            raise ValueError("O maximo esperado por dia nao pode ser menor que o minimo.")
        if self.usage_mode == PrescriptionUsageMode.FIXED and (
            self.min_expected_per_day is not None or self.max_expected_per_day is not None
        ):
            raise ValueError("Faixas esperadas por dia sao usadas apenas em prescricoes variaveis ou sob demanda.")
        return self


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionUpdate(BaseModel):
    patient_id: UUID | None = None
    item_id: UUID | None = None
    dose_amount: Decimal | None = Field(default=None, gt=0)
    frequency_per_day: int | None = Field(default=None, gt=0)
    specific_times: list[str] | None = None
    usage_mode: PrescriptionUsageMode | None = None
    comparison_window: PrescriptionComparisonWindow | None = None
    min_expected_per_day: Decimal | None = Field(default=None, ge=0)
    max_expected_per_day: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None

    @field_validator("specific_times")
    @classmethod
    def validate_specific_times(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value

        normalized_times: list[str] = []
        for time_value in value:
            normalized_time = time_value.strip()
            parts = normalized_time.split(":")
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                raise ValueError("Os horarios devem estar no formato HH:MM.")
            hour, minute = int(parts[0]), int(parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError("Os horarios devem estar no formato HH:MM.")
            normalized_times.append(f"{hour:02d}:{minute:02d}")

        if len(set(normalized_times)) != len(normalized_times):
            raise ValueError("Os horarios especificos nao podem se repetir.")

        return normalized_times


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    item_id: UUID
    dose_amount: Decimal
    frequency_per_day: int
    specific_times: list[str] | None
    usage_mode: PrescriptionUsageMode
    comparison_window: PrescriptionComparisonWindow
    min_expected_per_day: Decimal | None
    max_expected_per_day: Decimal | None
    start_date: date
    end_date: date | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PrescriptionDetailEnvelope(BaseModel):
    data: PrescriptionResponse


class PrescriptionListEnvelope(BaseModel):
    data: list[PrescriptionResponse]
    total: int


class PrescriptionMessageEnvelope(BaseModel):
    message: str
    data: PrescriptionResponse
