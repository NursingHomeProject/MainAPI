from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UnitBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized_value = " ".join(value.split()).strip()
        if not normalized_value:
            raise ValueError("O nome da unidade e obrigatorio.")
        return normalized_value

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("O simbolo da unidade e obrigatorio.")
        return normalized_value


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    symbol: str | None = Field(default=None, min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = " ".join(value.split()).strip()
        if not normalized_value:
            raise ValueError("O nome da unidade e obrigatorio.")
        return normalized_value

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("O simbolo da unidade e obrigatorio.")
        return normalized_value


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    symbol: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UnitDetailEnvelope(BaseModel):
    data: UnitResponse


class UnitListEnvelope(BaseModel):
    data: list[UnitResponse]
    total: int


class UnitMessageEnvelope(BaseModel):
    message: str
    data: UnitResponse
