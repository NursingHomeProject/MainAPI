import type { ApiEnvelope, ApiListEnvelope } from "@/types/api"

export type ItemType = "medication" | "supply"

export type Item = {
  id: string
  name: string
  item_type: ItemType
  unit_id: string
  description: string | null
  sku: string | null
  minimum_stock: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ItemCreatePayload = {
  name: string
  item_type: ItemType
  unit_id: string
  description: string | null
  minimum_stock: string
  is_active: boolean
}

export type ItemUpdatePayload = Partial<ItemCreatePayload>

export type ItemListResponse = ApiListEnvelope<Item>
export type ItemDetailResponse = ApiEnvelope<Item>
