const AUTH_TOKEN_STORAGE_KEY = "casa-assistencial.auth-token"

export function readStoredAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
}

export function storeAuthToken(token: string) {
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token)
}

export function clearStoredAuthToken() {
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
}
