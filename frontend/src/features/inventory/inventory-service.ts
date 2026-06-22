import { http } from "@/services/http"
import type {
  InventoryMovementCreatePayload,
  InventoryMovementDetailResponse,
  InventoryMovementFilters,
  InventoryMovementListResponse,
  ItemStockDetailResponse,
  PatientStockEntryPayload,
  PatientStockListResponse,
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

export function getPatientStock(token: string, patientId: string) {
  return http.get<PatientStockListResponse>(`/patients/${patientId}/stock`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function createPatientStockEntry(
  token: string,
  patientId: string,
  payload: PatientStockEntryPayload,
) {
  return http.post<InventoryMovementDetailResponse>(
    `/patients/${patientId}/stock/movements`,
    JSON.stringify(payload),
    { headers: buildAuthHeaders(token) },
  )
}

// ── Administração de doses ─────────────────────────────────────────────────
// ANTI-FRAUDE: occurred_at é deliberadamente ausente deste tipo e desta função.
// O timestamp é sempre capturado pelo servidor (server_default=func.now() no banco).
// O frontend nunca envia nem expõe campo de data/hora para administrações.

export type AdministrationPayload = {
  item_id: string
  quantity: string
  notes?: string | null
}

export function registerDoseAdministration(
  token: string,
  patientId: string,
  payload: AdministrationPayload,
) {
  return createInventoryMovement(token, {
    item_id: payload.item_id,
    movement_type: "administration",
    adjustment_operation: null,
    quantity: payload.quantity,
    patient_id: patientId,
    notes: payload.notes ?? null,
  })
}
