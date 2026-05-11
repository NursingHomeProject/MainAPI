import { http } from "@/services/http"
import type { AuthUser, LoginResponse } from "@/types/auth"

function buildAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  }
}

export async function loginRequest(email: string, password: string) {
  const body = new URLSearchParams({
    username: email,
    password,
  })

  return http.post<LoginResponse>("/auth/login", body, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  })
}

export async function getCurrentUser(token: string) {
  return http.get<AuthUser>("/auth/me", {
    headers: buildAuthHeaders(token),
  })
}
