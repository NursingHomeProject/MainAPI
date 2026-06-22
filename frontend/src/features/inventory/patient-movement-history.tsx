import { useEffect, useState } from "react"
import { History } from "lucide-react"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { listInventoryMovements } from "@/features/inventory/inventory-service"
import { HttpError } from "@/services/http"
import type { InventoryMovement, InventoryMovementType } from "@/types/inventory"

type PatientMovementHistoryProps = {
  patientId: string
  itemId: string
  token: string
}

const MOVEMENT_LABEL: Record<InventoryMovementType, string> = {
  entry: "Entrada",
  administration: "Administração",
  loss: "Perda",
  discard: "Descarte",
  adjustment: "Ajuste",
}

const MOVEMENT_COLOR: Record<InventoryMovementType, string> = {
  entry: "text-emerald-700",
  administration: "text-muted-foreground",
  loss: "text-red-600",
  discard: "text-red-600",
  adjustment: "text-amber-700",
}

const EFFECT_COLOR: Record<string, string> = {
  positive: "text-emerald-700 font-medium",
  negative: "text-red-600 font-medium",
  neutral: "text-foreground",
}

function formatOccurredAt(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value))
}

function formatEffect(stockEffect: string, unitSymbol?: string): string {
  const num = Number(stockEffect)
  const sign = num >= 0 ? "+" : ""
  const formatted = Math.abs(num) % 1 === 0
    ? Math.abs(num).toLocaleString("pt-BR")
    : Math.abs(num).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 3 })
  return `${sign}${num < 0 ? "-" : ""}${formatted}${unitSymbol ? " " + unitSymbol : ""}`
}

function effectColorClass(stockEffect: string): string {
  const num = Number(stockEffect)
  if (num > 0) return EFFECT_COLOR.positive
  if (num < 0) return EFFECT_COLOR.negative
  return EFFECT_COLOR.neutral
}

function getErrorMessage(error: unknown): string {
  if (error instanceof HttpError) return error.message
  if (error instanceof Error) return error.message
  return "Não foi possível carregar o histórico."
}

export function PatientMovementHistory({
  patientId,
  itemId,
  token,
}: PatientMovementHistoryProps) {
  const [movements, setMovements] = useState<InventoryMovement[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listInventoryMovements(token, { patient_id: patientId, item_id: itemId })
      .then((res) => {
        if (!cancelled) {
          // Ordena por occurred_at desc e pega as 10 últimas
          const sorted = [...res.data].sort(
            (a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime(),
          )
          setMovements(sorted.slice(0, 10))
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [patientId, itemId, token])

  if (loading) {
    return (
      <div className="mt-3 rounded-xl border border-border/60 bg-background/60 px-4 py-3 text-sm text-muted-foreground">
        Carregando histórico...
      </div>
    )
  }

  if (error) {
    return (
      <div className="mt-3">
        <FeedbackBanner message={error} variant="error" />
      </div>
    )
  }

  if (movements.length === 0) {
    return (
      <div className="mt-3 flex items-center gap-2 rounded-xl border border-dashed border-border/70 bg-background/60 px-4 py-3 text-sm text-muted-foreground">
        <History className="h-4 w-4 shrink-0" />
        Nenhuma movimentação registrada ainda.
      </div>
    )
  }

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-border/60 bg-background/60">
      <div className="flex items-center gap-2 border-b border-border/60 px-4 py-2.5">
        <History className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Últimas {movements.length} movimentações
        </span>
      </div>
      <ul className="divide-y divide-border/50">
        {movements.map((mov) => (
          <li key={mov.id} className="flex items-start justify-between gap-3 px-4 py-2.5 text-sm">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <span className={MOVEMENT_COLOR[mov.movement_type]}>
                  {MOVEMENT_LABEL[mov.movement_type]}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatOccurredAt(mov.occurred_at)}
                </span>
                {mov.created_by_user_name ? (
                  <span className="text-xs text-muted-foreground">· {mov.created_by_user_name}</span>
                ) : null}
              </div>
              {mov.notes ? (
                <p className="mt-0.5 truncate text-xs text-muted-foreground">{mov.notes}</p>
              ) : null}
            </div>
            <span className={`shrink-0 tabular-nums ${effectColorClass(mov.stock_effect)}`}>
              {formatEffect(mov.stock_effect)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
