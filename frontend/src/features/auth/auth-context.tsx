import {
  createContext,
  type ReactNode,
  useEffect,
  useState,
} from "react"

import { getCurrentUser, loginRequest } from "@/features/auth/auth-service"
import {
  clearStoredAuthToken,
  readStoredAuthToken,
  storeAuthToken,
} from "@/features/auth/auth-storage"
import type { AuthUser } from "@/types/auth"

type AuthStatus = "loading" | "authenticated" | "unauthenticated"

type AuthContextValue = {
  isAuthenticated: boolean
  isLoading: boolean
  status: AuthStatus
  token: string | null
  user: AuthUser | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => readStoredAuthToken())
  const [user, setUser] = useState<AuthUser | null>(null)
  const [status, setStatus] = useState<AuthStatus>(() =>
    readStoredAuthToken() ? "loading" : "unauthenticated",
  )

  async function applyAuthenticatedSession(activeToken: string) {
    const user = await getCurrentUser(activeToken)
    storeAuthToken(activeToken)
    setToken(activeToken)
    setUser(user)
    setStatus("authenticated")
  }

  function clearSession() {
    clearStoredAuthToken()
    setToken(null)
    setUser(null)
    setStatus("unauthenticated")
  }

  async function signIn(email: string, password: string) {
    const response = await loginRequest(email, password)
    await applyAuthenticatedSession(response.access_token)
  }

  function signOut() {
    clearSession()
  }

  async function refreshUser() {
    if (!token) {
      clearSession()
      return
    }

    setStatus("loading")

    try {
      const user = await getCurrentUser(token)
      setUser(user)
      setStatus("authenticated")
    } catch {
      clearSession()
      throw new Error("Não foi possível atualizar a sessão.")
    }
  }

  useEffect(() => {
    let isMounted = true

    async function restoreSession() {
      const storedToken = readStoredAuthToken()

      if (!storedToken) {
        if (isMounted) {
          setStatus("unauthenticated")
        }
        return
      }

      try {
        const user = await getCurrentUser(storedToken)

        if (!isMounted) {
          return
        }

        setToken(storedToken)
        setUser(user)
        setStatus("authenticated")
      } catch {
        if (isMounted) {
          clearSession()
        }
      }
    }

    void restoreSession()

    return () => {
      isMounted = false
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: status === "authenticated",
        isLoading: status === "loading",
        refreshUser,
        signIn,
        signOut,
        status,
        token,
        user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export { AuthContext }
