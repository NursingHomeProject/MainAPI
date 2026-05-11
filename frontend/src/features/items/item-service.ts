import { http } from "@/services/http"
import type { ItemCreatePayload, ItemDetailResponse, ItemListResponse, ItemUpdatePayload } from "@/types/item"

function buildAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  }
}

export function listItems(token: string) {
  return http.get<ItemListResponse>("/items?include_inactive=true", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function getItem(token: string, itemId: string) {
  return http.get<ItemDetailResponse>(`/items/${itemId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function createItem(token: string, payload: ItemCreatePayload) {
  return http.post<ItemDetailResponse>("/items", JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}

export function updateItem(token: string, itemId: string, payload: ItemUpdatePayload) {
  return http.put<ItemDetailResponse>(`/items/${itemId}`, JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}
