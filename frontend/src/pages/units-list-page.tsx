import { useCallback, useEffect, useState } from "react"
import { Plus, Ruler, SquarePen } from "lucide-react"
import { Link, useLocation, useNavigate } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/features/auth/use-auth"
import { listUnits } from "@/features/units/unit-service"
import { HttpError } from "@/services/http"
import type { Unit } from "@/types/unit"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível carregar as unidades."
}

export function UnitsListPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { token } = useAuth()
  const [units, setUnits] = useState<Unit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const flashState = location.state as { message?: string; tone?: "success" | "error" } | null

  const loadUnits = useCallback(async () => {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setUnits([])
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await listUnits(token)
      setUnits(response.data)
    } catch (requestError) {
      setUnits([])
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [token])

  useEffect(() => {
    void loadUnits()
  }, [loadUnits])

  useEffect(() => {
    if (!flashState?.message) {
      return
    }

    navigate(location.pathname, { replace: true })
  }, [flashState?.message, location.pathname, navigate])

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <>
            <Button onClick={() => void loadUnits()} variant="outline">
              Atualizar
            </Button>
            <Button asChild>
              <Link to="/units/new">
                <Plus className="h-4 w-4" />
                Nova unidade
              </Link>
            </Button>
          </>
        }
        description="Organize as unidades de medida usadas no cadastro de itens e prescrições."
        title="Unidades de medida"
      />

      {error ? <FeedbackBanner message={error} variant="error" /> : null}

      {flashState?.message ? (
        <FeedbackBanner message={flashState.message} variant={flashState.tone === "success" ? "success" : "error"} />
      ) : null}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Card className="bg-white/92" key={index}>
              <CardHeader>
                <div className="h-5 w-24 animate-pulse rounded bg-secondary" />
                <div className="h-4 w-40 animate-pulse rounded bg-secondary" />
              </CardHeader>
              <CardContent>
                <div className="h-4 w-full animate-pulse rounded bg-secondary" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {!isLoading && units.length === 0 ? (
        <Card className="bg-white/92">
          <CardContent>
            <EmptyState
              action={
                <Button asChild>
                  <Link to="/units/new">Criar primeira unidade</Link>
                </Button>
              }
              description="Cadastre a primeira unidade para organizar os itens do sistema."
              icon={Ruler}
              title="Nenhuma unidade encontrada"
            />
          </CardContent>
        </Card>
      ) : null}

      {!isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {units.map((unit) => (
            <Card className="bg-white/92" key={unit.id}>
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>{unit.name}</CardTitle>
                    <CardDescription>Simbolo: {unit.symbol}</CardDescription>
                  </div>
                  <Badge variant={unit.is_active ? "success" : "outline"}>
                    {unit.is_active ? "Ativa" : "Inativa"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="min-h-12 text-sm text-muted-foreground">
                  {unit.description?.trim() || "Sem descrição cadastrada."}
                </p>
                <div className="flex flex-wrap gap-3">
                  <Button asChild size="sm">
                    <Link to={`/units/${unit.id}/edit`}>
                      <SquarePen className="h-4 w-4" />
                      Editar
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  )
}
