from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.clock import normalize_datetime_to_project_timezone
from app.modules.inventory.models import InventoryAdjustmentOperation, InventoryMovementType
from app.modules.items.models import ItemType


class InventoryMovementCreate(BaseModel):
    item_id: UUID
    movement_type: InventoryMovementType
    adjustment_operation: InventoryAdjustmentOperation | None = None
    quantity: Decimal = Field(gt=0)
    patient_id: UUID | None = None
    prescription_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    occurred_at: datetime | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = " ".join(value.split()).strip()
        return normalized_value or None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        return normalize_datetime_to_project_timezone(value)

    @model_validator(mode="after")
    def validate_adjustment_requirements(self) -> "InventoryMovementCreate":
        if self.movement_type == InventoryMovementType.ADJUSTMENT and self.adjustment_operation is None:
            raise ValueError("adjustment_operation e obrigatorio para movimentacoes do tipo adjustment.")
        if self.movement_type != InventoryMovementType.ADJUSTMENT and self.adjustment_operation is not None:
            raise ValueError("adjustment_operation so pode ser enviado para movimentacoes do tipo adjustment.")
        return self


class InventoryMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID
    unit_id: UUID
    patient_id: UUID | None
    prescription_id: UUID | None
    created_by_user_id: UUID | None
    movement_type: InventoryMovementType
    adjustment_operation: InventoryAdjustmentOperation | None
    quantity: Decimal
    stock_effect: Decimal
    reason: str | None
    notes: str | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime


class InventoryMovementDetailEnvelope(BaseModel):
    data: InventoryMovementResponse


class InventoryMovementListEnvelope(BaseModel):
    data: list[InventoryMovementResponse]
    total: int


class ItemStockResponse(BaseModel):
    item_id: UUID
    item_name: str
    item_type: ItemType
    unit_id: UUID
    unit_name: str
    unit_symbol: str
    current_stock: Decimal
    minimum_stock: Decimal
    is_below_minimum: bool


class ItemStockDetailEnvelope(BaseModel):
    data: ItemStockResponse
