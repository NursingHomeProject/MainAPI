import type { ReactNode } from "react"
import { LoaderCircle, LockKeyhole } from "lucide-react"
import { Navigate, Outlet, useLocation } from "react-router-dom"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/features/auth/use-auth"

export function AuthGuard() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(15,118,110,0.14),_transparent_28%),linear-gradient(180deg,#f8faf8_0%,#f4f1e6_100%)] px-4">
        <Card className="w-full max-w-md bg-white/92">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LoaderCircle className="h-5 w-5 animate-spin text-primary" />
              Restaurando sessão
            </CardTitle>
            <CardDescription>Estamos preparando seu acesso ao sistema.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Aguarde um instante. Se necessario, voce sera direcionado para a tela de login.
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate replace state={{ from: location }} to="/login" />
  }

  return <Outlet />
}

export function LoginGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(15,118,110,0.14),_transparent_28%),linear-gradient(180deg,#f8faf8_0%,#f4f1e6_100%)] px-4">
        <Card className="w-full max-w-md bg-white/92">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LoaderCircle className="h-5 w-5 animate-spin text-primary" />
              Carregando sessão
            </CardTitle>
            <CardDescription>Verificando seu acesso.</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate replace to="/" />
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(15,118,110,0.14),_transparent_28%),linear-gradient(180deg,#f8faf8_0%,#f4f1e6_100%)] px-4 py-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center justify-center">
        <div className="hidden max-w-xl flex-1 pr-10 lg:block">
          <div className="rounded-[2rem] border border-emerald-900/10 bg-[linear-gradient(135deg,rgba(10,75,63,0.96),rgba(14,110,94,0.96))] p-10 text-white shadow-soft">
            <div className="mb-6 inline-flex rounded-full border border-white/15 bg-white/10 p-3">
              <LockKeyhole className="h-5 w-5" />
            </div>
            <h1 className="text-4xl font-semibold leading-tight">
              Acesso ao painel da casa assistencial.
            </h1>
            <p className="mt-4 text-base text-emerald-50/85">
              Entre com seu e-mail e senha para acompanhar pacientes, prescrições, estoque e alertas.
            </p>
          </div>
        </div>
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  )
}
