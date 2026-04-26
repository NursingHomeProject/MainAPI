import type { ApiEnvelope } from "@/types/api"

export type AuthUser = {
  id: string
  full_name: string
  email: string
  is_active: boolean
  is_superuser: boolean
}

export type LoginResponse = {
  access_token: string
  token_type: string
}

export type CurrentUserResponse = ApiEnvelope<AuthUser>
