from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.items.models import ItemType


class ItemBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    item_type: ItemType
    unit_id: UUID
    description: str | None = Field(default=None, max_length=1000)
    sku: str | None = Field(default=None, max_length=100)
    minimum_stock: Decimal = Field(default=Decimal("0"))
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized_value = " ".join(value.split()).strip()
        if len(normalized_value) < 2:
            raise ValueError("O nome do item deve ter pelo menos 2 caracteres.")
        return normalized_value

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("minimum_stock")
    @classmethod
    def validate_minimum_stock(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("O estoque minimo nao pode ser negativo.")
        return value


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    item_type: ItemType | None = None
    unit_id: UUID | None = None
    description: str | None = Field(default=None, max_length=1000)
    sku: str | None = Field(default=None, max_length=100)
    minimum_stock: Decimal | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = " ".join(value.split()).strip()
        if len(normalized_value) < 2:
            raise ValueError("O nome do item deve ter pelo menos 2 caracteres.")
        return normalized_value

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("minimum_stock")
    @classmethod
    def validate_minimum_stock(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("O estoque minimo nao pode ser negativo.")
        return value


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    item_type: ItemType
    unit_id: UUID
    description: str | None
    sku: str | None
    minimum_stock: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ItemDetailEnvelope(BaseModel):
    data: ItemResponse


class ItemListEnvelope(BaseModel):
    data: list[ItemResponse]
    total: int


class ItemMessageEnvelope(BaseModel):
    message: str
    data: ItemResponse
