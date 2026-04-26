import { type FormEvent, useState } from "react"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { NativeSelect } from "@/components/app/native-select"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type {
  InventoryAdjustmentOperation,
  InventoryMovementCreatePayload,
  InventoryMovementType,
} from "@/types/inventory"
import type { Item } from "@/types/item"
import type { Patient } from "@/types/patient"

export type InventoryMovementFormValues = InventoryMovementCreatePayload

type InventoryMovementFormProps = {
  defaultItemId?: string
  error: string | null
  isSubmitting: boolean
  items: Item[]
  itemsLoading: boolean
  patients: Patient[]
  patientsLoading: boolean
  onSubmit: (values: InventoryMovementFormValues) => Promise<void>
}

const movementTypeOptions: Array<{ label: string; value: InventoryMovementType }> = [
  { label: "Entrada", value: "entry" },
  { label: "Administração", value: "administration" },
  { label: "Perda", value: "loss" },
  { label: "Ajuste", value: "adjustment" },
  { label: "Descarte", value: "discard" },
]

const adjustmentOperationOptions: Array<{ label: string; value: InventoryAdjustmentOperation }> = [
  { label: "Aumentar saldo", value: "increase" },
  { label: "Reduzir saldo", value: "decrease" },
]

export function InventoryMovementForm({
  defaultItemId = "",
  error,
  isSubmitting,
  items,
  itemsLoading,
  onSubmit,
  patients,
  patientsLoading,
}: InventoryMovementFormProps) {
  const [values, setValues] = useState<InventoryMovementFormValues>({
    item_id: defaultItemId,
    movement_type: "entry",
    adjustment_operation: null,
    quantity: "1",
    patient_id: null,
    notes: null,
  })

  const activeItems = items.filter((item) => item.is_active)
  const administrationRequiresPatient = values.movement_type === "administration"
  const requiresAdjustmentOperation = values.movement_type === "adjustment"

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      item_id: values.item_id,
      movement_type: values.movement_type,
      adjustment_operation: requiresAdjustmentOperation ? values.adjustment_operation : null,
      quantity: values.quantity,
      patient_id: administrationRequiresPatient ? values.patient_id : null,
      notes: values.notes?.trim() ? values.notes.trim() : null,
    })

    setValues((current) => ({
      item_id: current.item_id,
      movement_type: "entry",
      adjustment_operation: null,
      quantity: "1",
      patient_id: null,
      notes: null,
    }))
  }

  return (
    <Card className="bg-white/92">
      <CardHeader>
        <CardTitle>Lancar movimentacao</CardTitle>
        <CardDescription>Registre entradas, administrações, perdas, ajustes ou descartes.</CardDescription>
      </CardHeader>
      <CardContent>
        {itemsLoading || patientsLoading ? (
          <div className="rounded-2xl border border-border/80 bg-secondary/20 px-4 py-6 text-sm text-muted-foreground">
            Carregando itens e pacientes...
          </div>
        ) : activeItems.length === 0 ? (
          <FeedbackBanner
            message="Não ha itens ativos disponiveis para movimentacao. Cadastre um item ativo antes de testar estoque."
            variant="warning"
          />
        ) : (
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="movement-item">Item</Label>
                <NativeSelect
                  id="movement-item"
                  onChange={(event) => setValues((current) => ({ ...current, item_id: event.target.value }))}
                  required
                  value={values.item_id}
                >
                  <option value="">Selecione um item</option>
                  {activeItems.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </NativeSelect>
              </div>

              <div className="space-y-2">
                <Label htmlFor="movement-type">Tipo de movimentacao</Label>
                <NativeSelect
                  id="movement-type"
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      movement_type: event.target.value as InventoryMovementType,
                      adjustment_operation: event.target.value === "adjustment" ? current.adjustment_operation : null,
                      patient_id: event.target.value === "administration" ? current.patient_id : null,
                    }))
                  }
                  value={values.movement_type}
                >
                  {movementTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </NativeSelect>
              </div>

              <div className="space-y-2">
                <Label htmlFor="movement-quantity">Quantidade</Label>
                <Input
                  id="movement-quantity"
                  inputMode="decimal"
                  onChange={(event) => setValues((current) => ({ ...current, quantity: event.target.value }))}
                  placeholder="1"
                  required
                  value={values.quantity}
                />
              </div>

              {requiresAdjustmentOperation ? (
                <div className="space-y-2">
                  <Label htmlFor="adjustment-operation">Operação do ajuste</Label>
                  <NativeSelect
                    id="adjustment-operation"
                    onChange={(event) =>
                      setValues((current) => ({
                        ...current,
                        adjustment_operation: event.target.value as InventoryAdjustmentOperation,
                      }))
                    }
                    required
                    value={values.adjustment_operation ?? ""}
                  >
                    <option value="">Selecione a operação</option>
                    {adjustmentOperationOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </NativeSelect>
                </div>
              ) : null}

              {administrationRequiresPatient ? (
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="movement-patient">Paciente</Label>
                  <NativeSelect
                    id="movement-patient"
                    onChange={(event) =>
                      setValues((current) => ({
                        ...current,
                        patient_id: event.target.value || null,
                      }))
                    }
                    required
                    value={values.patient_id ?? ""}
                  >
                    <option value="">Selecione um paciente</option>
                    {patients.map((patient) => (
                      <option key={patient.id} value={patient.id}>
                        {patient.full_name}
                        {patient.is_active ? "" : " - inativo"}
                      </option>
                    ))}
                  </NativeSelect>
                  <p className="text-xs text-muted-foreground">
                    Ao registrar uma administração, selecione o paciente que recebeu o item.
                  </p>
                </div>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="movement-notes">Notas</Label>
              <Textarea
                id="movement-notes"
                maxLength={2000}
                onChange={(event) => setValues((current) => ({ ...current, notes: event.target.value || null }))}
                placeholder="Observações opcionais sobre a movimentacao."
                value={values.notes ?? ""}
              />
            </div>

            {error ? <FeedbackBanner message={error} variant="error" /> : null}

            <div className="flex justify-end">
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? "Salvando..." : "Lancar movimentacao"}
              </Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
