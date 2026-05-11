import { http } from "@/services/http"
import type {
  InventoryMovementCreatePayload,
  InventoryMovementDetailResponse,
  InventoryMovementFilters,
  InventoryMovementListResponse,
  ItemStockDetailResponse,
} from "@/types/inventory"

function buildAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  }
}

function buildInventoryMovementsQuery(filters: InventoryMovementFilters = {}) {
  const searchParams = new URLSearchParams()

  if (filters.item_id) {
    searchParams.set("item_id", filters.item_id)
  }

  if (filters.patient_id) {
    searchParams.set("patient_id", filters.patient_id)
  }

  if (filters.movement_type) {
    searchParams.set("movement_type", filters.movement_type)
  }

  const queryString = searchParams.toString()
  return queryString ? `/inventory/movements?${queryString}` : "/inventory/movements"
}

export function listInventoryMovements(token: string, filters: InventoryMovementFilters = {}) {
  return http.get<InventoryMovementListResponse>(buildInventoryMovementsQuery(filters), {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function createInventoryMovement(token: string, payload: InventoryMovementCreatePayload) {
  return http.post<InventoryMovementDetailResponse>("/inventory/movements", JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}

export function getItemStock(token: string, itemId: string) {
  return http.get<ItemStockDetailResponse>(`/items/${itemId}/stock`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}
