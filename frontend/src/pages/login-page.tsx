import { type FormEvent, useState } from "react"
import { LogIn } from "lucide-react"
import { Navigate, useLocation, useNavigate } from "react-router-dom"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoginGuard } from "@/features/auth/auth-guard"
import { useAuth } from "@/features/auth/use-auth"
import { HttpError } from "@/services/http"

type LoginLocationState = {
  from?: {
    pathname?: string
    search?: string
  }
}

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível concluir o login."
}

function LoginPageContent() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, signIn } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const locationState = location.state as LoginLocationState | null
  const redirectTo = `${locationState?.from?.pathname || "/dashboard"}${locationState?.from?.search || ""}`
  const canSubmit = email.trim().length > 0 && password.length > 0

  if (isAuthenticated) {
    return <Navigate replace to={redirectTo} />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await signIn(email, password)
      navigate(redirectTo, { replace: true })
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="border-border/70 bg-white/92 shadow-soft">
      <CardHeader>
        <CardTitle className="text-2xl">Entrar no painel</CardTitle>
        <CardDescription>Informe seus dados para acessar o sistema.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="email">E-mail</Label>
            <Input
              autoComplete="username"
              id="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@casa.local"
              type="email"
              value={email}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Senha</Label>
            <Input
              autoComplete="current-password"
              id="password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Sua senha"
              type="password"
              value={password}
            />
          </div>

          {error ? <FeedbackBanner message={error} variant="error" /> : null}

          <Button className="w-full" disabled={isSubmitting || !canSubmit} type="submit">
            <LogIn className="h-4 w-4" />
            {isSubmitting ? "Entrando..." : "Entrar"}
          </Button>

          <FeedbackBanner
            message="Depois do login, voce sera direcionado para a visão geral do sistema."
            variant="info"
          />
        </form>
      </CardContent>
    </Card>
  )
}

export function LoginPage() {
  return (
    <LoginGuard>
      <LoginPageContent />
    </LoginGuard>
  )
}
