from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PatientBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=255)
    birth_date: date | None = None
    care_notes: str | None = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized_value = " ".join(value.split())
        if len(normalized_value) < 3:
            raise ValueError("O nome do paciente deve ter pelo menos 3 caracteres.")
        return normalized_value

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("A data de nascimento nao pode estar no futuro.")
        return value


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=255)
    birth_date: date | None = None
    care_notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = " ".join(value.split())
        if len(normalized_value) < 3:
            raise ValueError("O nome do paciente deve ter pelo menos 3 caracteres.")
        return normalized_value

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("A data de nascimento nao pode estar no futuro.")
        return value


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    birth_date: date | None
    care_notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PatientDetailEnvelope(BaseModel):
    data: PatientResponse


class PatientListEnvelope(BaseModel):
    data: list[PatientResponse]
    total: int


class PatientMessageEnvelope(BaseModel):
    message: str
    data: PatientResponse
