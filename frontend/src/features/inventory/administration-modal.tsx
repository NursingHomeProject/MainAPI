import { useEffect, useState } from "react"
import { Syringe } from "lucide-react"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { registerDoseAdministration } from "@/features/inventory/inventory-service"
import { HttpError } from "@/services/http"
import type { PatientItemStock } from "@/types/inventory"
import { formatDecimalAsInteger } from "@/lib/utils"

type AdministrationModalProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  patientId: string
  item: PatientItemStock
  doseAmount: string
  token: string
  onSuccess: () => void
}

function getErrorMessage(error: unknown): string {
  if (error instanceof HttpError) return error.message
  if (error instanceof Error) return error.message
  return "Não foi possível registrar a administração. Tente novamente."
}

export function AdministrationModal({
  open,
  onOpenChange,
  patientId,
  item,
  doseAmount,
  token,
  onSuccess,
}: AdministrationModalProps) {
  const [quantity, setQuantity] = useState("")
  const [notes, setNotes] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Pré-preenche a dose prescrita sempre que o modal abre.
  // parseFloat remove zeros desnecessários vindos do backend (ex: "1.000" → "1")
  useEffect(() => {
    if (open) {
      const parsed = parseFloat(doseAmount)
      setQuantity(isNaN(parsed) ? doseAmount : String(parsed))
      setNotes("")
      setError(null)
    }
  }, [open, doseAmount])

  function handleClose() {
    if (loading) return
    onOpenChange(false)
    // Limpa o formulário com pequeno delay para a animação fechar antes
    setTimeout(() => {
      setQuantity("")
      setNotes("")
      setError(null)
    }, 150)
  }

  async function handleSubmit() {
    const parsed = parseFloat(quantity)
    if (!quantity || isNaN(parsed) || parsed <= 0) {
      setError("Informe uma quantidade válida.")
      return
    }

    setLoading(true)
    setError(null)

    try {
      await registerDoseAdministration(token, patientId, {
        item_id: item.item_id,
        quantity,
        notes: notes.trim() || null,
      })
      onSuccess()
      handleClose()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const isDisabled = loading || !quantity || parseFloat(quantity) <= 0

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[460px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Syringe className="h-4 w-4 text-primary" />
            Registrar administração
          </DialogTitle>
          <DialogDescription>{item.item_name}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Aviso de estoque baixo */}
          {item.is_below_minimum ? (
            <FeedbackBanner
              message="Atenção: estoque abaixo do mínimo. Verifique a disponibilidade antes de confirmar."
              variant="warning"
            />
          ) : null}

          {/* Saldo atual — somente leitura */}
          <div className="rounded-2xl border border-border/70 bg-secondary/35 p-3">
            <p className="text-xs text-muted-foreground">Saldo atual</p>
            <p
              className={`mt-1 text-lg font-semibold ${
                item.is_below_minimum ? "text-red-600" : "text-foreground"
              }`}
            >
              {formatDecimalAsInteger(item.current_stock)} {item.unit_symbol}
            </p>
          </div>

          {/* Dose a administrar */}
          <div className="space-y-2">
            <Label htmlFor="admin-quantity">
              Dose a administrar <span className="text-red-500">*</span>
            </Label>
            <Input
              autoFocus
              className={
                error?.toLowerCase().includes("quantidade")
                  ? "border-red-500 focus-visible:ring-red-500"
                  : ""
              }
              id="admin-quantity"
              inputMode="decimal"
              min="0.001"
              onChange={(e) => {
                setQuantity(e.target.value)
                if (error?.toLowerCase().includes("quantidade")) setError(null)
              }}
              step="any"
              type="number"
              value={quantity}
            />
            <p className="text-xs text-muted-foreground">
              Unidade: {item.unit_symbol} · Dose prescrita: {formatDecimalAsInteger(doseAmount)}{" "}
              {item.unit_symbol}
            </p>
          </div>

          {/* Observações */}
          <div className="space-y-2">
            <Label htmlFor="admin-notes">Observações</Label>
            <Textarea
              id="admin-notes"
              maxLength={2000}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Registro opcional (ex: intercorrência, reação observada...)"
              rows={3}
              value={notes}
            />
          </div>

          {/* Erro */}
          {error ? <FeedbackBanner message={error} variant="error" /> : null}

          {/* Rodapé anti-fraude */}
          <p className="text-xs text-muted-foreground">
            O horário de administração é registrado automaticamente pelo sistema no momento da
            confirmação.
          </p>
        </div>

        <DialogFooter>
          <Button disabled={loading} onClick={handleClose} variant="outline">
            Cancelar
          </Button>
          <Button disabled={isDisabled} onClick={() => void handleSubmit()}>
            {loading ? "Salvando..." : "Confirmar administração"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
