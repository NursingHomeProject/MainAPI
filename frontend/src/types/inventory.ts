import type { ApiEnvelope, ApiListEnvelope } from "@/types/api"
import type { ItemType } from "@/types/item"

export type InventoryMovementType = "entry" | "administration" | "loss" | "adjustment" | "discard"
export type InventoryAdjustmentOperation = "increase" | "decrease"

export type InventoryMovement = {
  id: string
  item_id: string
  unit_id: string
  patient_id: string | null
  prescription_id: string | null
  created_by_user_id: string | null
  movement_type: InventoryMovementType
  adjustment_operation: InventoryAdjustmentOperation | null
  quantity: string
  stock_effect: string
  reason: string | null
  notes: string | null
  occurred_at: string
  created_at: string
  updated_at: string
}

export type InventoryMovementCreatePayload = {
  item_id: string
  movement_type: InventoryMovementType
  adjustment_operation: InventoryAdjustmentOperation | null
  quantity: string
  patient_id: string | null
  notes: string | null
}

export type InventoryMovementFilters = {
  item_id?: string
  patient_id?: string
  movement_type?: InventoryMovementType
}

export type ItemStock = {
  item_id: string
  item_name: string
  item_type: ItemType
  unit_id: string
  unit_name: string
  unit_symbol: string
  current_stock: string
  minimum_stock: string
  is_below_minimum: boolean
}

export type InventoryMovementListResponse = ApiListEnvelope<InventoryMovement>
export type InventoryMovementDetailResponse = ApiEnvelope<InventoryMovement>
export type ItemStockDetailResponse = ApiEnvelope<ItemStock>
