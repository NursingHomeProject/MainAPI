import { useCallback, useEffect, useMemo, useState } from "react"
import { Activity, PackagePlus, Pill, SquarePen } from "lucide-react"
import { Link, useLocation, useNavigate } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/features/auth/use-auth"
import { listItems } from "@/features/items/item-service"
import { listUnits } from "@/features/units/unit-service"
import { formatDecimalAsInteger } from "@/lib/utils"
import { HttpError } from "@/services/http"
import type { Item } from "@/types/item"
import type { Unit } from "@/types/unit"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível carregar os itens."
}

function getItemTypeLabel(itemType: Item["item_type"]) {
  return itemType === "medication" ? "Medicamento" : "Insumo"
}

export function ItemsListPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { token } = useAuth()

  const [items, setItems] = useState<Item[]>([])
  const [units, setUnits] = useState<Unit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const flashState = location.state as { message?: string; tone?: "success" | "error" } | null

  const unitMap = useMemo(() => new Map(units.map((unit) => [unit.id, unit])), [units])

  const loadItems = useCallback(async () => {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setItems([])
      setUnits([])
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const [itemsResponse, unitsResponse] = await Promise.all([listItems(token), listUnits(token)])
      setItems(itemsResponse.data)
      setUnits(unitsResponse.data)
    } catch (requestError) {
      setItems([])
      setUnits([])
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [token])

  useEffect(() => {
    void loadItems()
  }, [loadItems])

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
            <Button onClick={() => void loadItems()} variant="outline">
              Atualizar
            </Button>
            <Button asChild>
              <Link to="/items/new">
                <PackagePlus className="h-4 w-4" />
                Novo item
              </Link>
            </Button>
          </>
        }
        description="Cadastre e acompanhe medicamentos e insumos utilizados no atendimento."
        title="Itens"
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
                <div className="h-5 w-28 animate-pulse rounded bg-secondary" />
                <div className="h-4 w-44 animate-pulse rounded bg-secondary" />
              </CardHeader>
              <CardContent>
                <div className="h-4 w-full animate-pulse rounded bg-secondary" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {!isLoading && items.length === 0 ? (
        <Card className="bg-white/92">
          <CardContent>
            <EmptyState
              action={
                <Button asChild>
                  <Link to="/items/new">Criar primeiro item</Link>
                </Button>
              }
              description="Cadastre o primeiro item para organizar o estoque e as prescrições."
              icon={Pill}
              title="Nenhum item encontrado"
            />
          </CardContent>
        </Card>
      ) : null}

      {!isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((item) => {
            const unit = unitMap.get(item.unit_id)

            return (
              <Card className="bg-white/92" key={item.id}>
                <CardHeader className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle>{item.name}</CardTitle>
                      <CardDescription>
                        {getItemTypeLabel(item.item_type)} • {unit ? `${unit.name} (${unit.symbol})` : item.unit_id}
                      </CardDescription>
                    </div>
                    <Badge variant={item.is_active ? "success" : "outline"}>
                      {item.is_active ? "Ativo" : "Inativo"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="min-h-12 text-sm text-muted-foreground">
                    {item.description?.trim() || "Sem descrição cadastrada."}
                  </p>
                  <div className="rounded-xl border border-border/70 bg-secondary/25 px-4 py-3 text-sm">
                    <p className="text-muted-foreground">Estoque mínimo</p>
                    <p className="font-medium text-foreground">{formatDecimalAsInteger(item.minimum_stock)}</p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/items/${item.id}`}>
                        <Activity className="h-4 w-4" />
                        Ver situação
                      </Link>
                    </Button>
                    <Button asChild size="sm">
                      <Link to={`/items/${item.id}/edit`}>
                        <SquarePen className="h-4 w-4" />
                        Editar
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
