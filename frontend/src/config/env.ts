const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "")

export const env = {
  apiBaseUrl,
} as const
