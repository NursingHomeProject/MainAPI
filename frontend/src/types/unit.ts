import type { ApiEnvelope, ApiListEnvelope } from "@/types/api"

export type Unit = {
  id: string
  name: string
  symbol: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type UnitCreatePayload = {
  name: string
  symbol: string
  description: string | null
  is_active: boolean
}

export type UnitUpdatePayload = Partial<UnitCreatePayload>

export type UnitListResponse = ApiListEnvelope<Unit>
export type UnitDetailResponse = ApiEnvelope<Unit>
