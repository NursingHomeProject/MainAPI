import { useState } from "react"
import { Package } from "lucide-react"

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
import { createPatientStockEntry } from "@/features/inventory/inventory-service"
import { HttpError } from "@/services/http"
import type { PatientItemStock } from "@/types/inventory"

type StockEntryModalProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  patientId: string
  item: PatientItemStock
  token: string
  onSuccess: () => void
}

function getErrorMessage(error: unknown): string {
  if (error instanceof HttpError) return error.message
  if (error instanceof Error) return error.message
  return "Não foi possível registrar a entrada. Tente novamente."
}

export function StockEntryModal({
  open,
  onOpenChange,
  patientId,
  item,
  token,
  onSuccess,
}: StockEntryModalProps) {
  const [quantity, setQuantity] = useState("")
  const [notes, setNotes] = useState("")
  const [occurredAt, setOccurredAt] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleClose() {
    if (loading) return
    onOpenChange(false)
    // Limpa o formulário com pequeno delay para a animação fechar antes
    setTimeout(() => {
      setQuantity("")
      setNotes("")
      setOccurredAt("")
      setError(null)
    }, 150)
  }

  async function handleConfirm() {
    if (!quantity || Number(quantity) <= 0) return
    setLoading(true)
    setError(null)
    try {
      await createPatientStockEntry(token, patientId, {
        item_id: item.item_id,
        quantity,
        notes: notes.trim() || null,
        occurred_at: occurredAt || null,
      })
      onSuccess()
      handleClose()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const isDisabled = loading || !quantity || Number(quantity) <= 0

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-4 w-4 text-primary" />
            Registrar entrada
          </DialogTitle>
          <DialogDescription>
            {item.item_name} — estoque atual:{" "}
            <span className="font-medium text-foreground">
              {Number(item.current_stock).toLocaleString("pt-BR")} {item.unit_symbol}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error ? <FeedbackBanner message={error} variant="error" /> : null}

          <div className="space-y-2">
            <Label htmlFor="entry-quantity">
              Quantidade ({item.unit_symbol}) <span className="text-red-500">*</span>
            </Label>
            <Input
              autoFocus
              id="entry-quantity"
              inputMode="decimal"
              min="0.001"
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="Ex: 30"
              step="1"
              type="number"
              value={quantity}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="entry-notes">Observações</Label>
            <Textarea
              id="entry-notes"
              maxLength={2000}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Ex: Família trouxe caixa nova"
              rows={2}
              value={notes}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="entry-date">
              Data da entrada{" "}
              <span className="text-xs font-normal text-muted-foreground">(opcional — deixe em branco para usar agora)</span>
            </Label>
            <Input
              id="entry-date"
              onChange={(e) => setOccurredAt(e.target.value)}
              type="datetime-local"
              value={occurredAt}
            />
          </div>
        </div>

        <DialogFooter>
          <Button disabled={loading} onClick={handleClose} variant="outline">
            Cancelar
          </Button>
          <Button disabled={isDisabled} onClick={() => void handleConfirm()}>
            {loading ? "Salvando..." : "Confirmar entrada"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
