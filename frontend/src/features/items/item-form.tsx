import { type FormEvent, useState } from "react"
import { Link } from "react-router-dom"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { NativeSelect } from "@/components/app/native-select"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { ItemCreatePayload, ItemType } from "@/types/item"
import type { Unit } from "@/types/unit"

export type ItemFormValues = ItemCreatePayload

type ItemFormProps = {
  defaultValues?: ItemFormValues
  description: string
  error: string | null
  isSubmitting: boolean
  submitLabel: string
  title: string
  units: Unit[]
  unitsError: string | null
  unitsLoading: boolean
  onCancel: () => void
  onSubmit: (values: ItemFormValues) => Promise<void>
}

const itemTypeOptions: Array<{ label: string; value: ItemType }> = [
  { label: "Medicamento", value: "medication" },
  { label: "Insumo", value: "supply" },
]

const defaultItemValues: ItemFormValues = {
  name: "",
  item_type: "medication",
  unit_id: "",
  description: "",
  minimum_stock: "0",
  is_active: true,
}

export function ItemForm({
  defaultValues,
  description,
  error,
  isSubmitting,
  onCancel,
  onSubmit,
  submitLabel,
  title,
  units,
  unitsError,
  unitsLoading,
}: ItemFormProps) {
  const [values, setValues] = useState<ItemFormValues>(defaultValues ?? defaultItemValues)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      name: values.name,
      item_type: values.item_type,
      unit_id: values.unit_id,
      description: values.description?.trim() ? values.description.trim() : null,
      minimum_stock: values.minimum_stock || "0",
      is_active: values.is_active,
    })
  }

  const canRenderUnitSelect = units.length > 0

  return (
    <Card className="bg-white/92">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {unitsLoading ? (
          <div className="rounded-2xl border border-border/80 bg-secondary/20 px-4 py-6 text-sm text-muted-foreground">
            Carregando unidades de medida...
          </div>
        ) : unitsError ? (
          <FeedbackBanner message={unitsError} variant="error" />
        ) : !canRenderUnitSelect ? (
          <FeedbackBanner
            message={
              <>
                Nenhuma unidade disponível. Crie uma unidade primeiro em{" "}
                <Link className="font-medium underline" to="/units/new">
                  /units/new
                </Link>
                .
              </>
            }
            variant="warning"
          />
        ) : (
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="name">Nome</Label>
                <Input
                  id="name"
                  maxLength={255}
                  minLength={2}
                  onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Ex.: Dipirona 500mg"
                  required
                  value={values.name}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="item_type">Tipo de item</Label>
                <NativeSelect
                  id="item_type"
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      item_type: event.target.value as ItemType,
                    }))
                  }
                  value={values.item_type}
                >
                  {itemTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </NativeSelect>
              </div>

              <div className="space-y-2">
                <Label htmlFor="unit_id">Unidade de medida</Label>
                <NativeSelect
                  id="unit_id"
                  onChange={(event) => setValues((current) => ({ ...current, unit_id: event.target.value }))}
                  required
                  value={values.unit_id}
                >
                  <option value="">Selecione uma unidade</option>
                  {units.map((unit) => (
                    <option
                      disabled={!unit.is_active && unit.id !== values.unit_id}
                      key={unit.id}
                      value={unit.id}
                    >
                      {unit.name} ({unit.symbol}){unit.is_active ? "" : " - inativa"}
                    </option>
                  ))}
                </NativeSelect>
              </div>

              <div className="space-y-2">
                <Label htmlFor="minimum_stock">Estoque mínimo</Label>
                <Input
                  id="minimum_stock"
                  inputMode="decimal"
                  onChange={(event) => setValues((current) => ({ ...current, minimum_stock: event.target.value }))}
                  placeholder="0"
                  value={values.minimum_stock}
                />
              </div>

              <div className="flex items-end">
                <label className="flex items-center gap-3 rounded-xl border border-border/70 bg-secondary/30 px-4 py-3 text-sm">
                  <input
                    checked={values.is_active}
                    className="h-4 w-4 accent-hsl(var(--primary))"
                    onChange={(event) => setValues((current) => ({ ...current, is_active: event.target.checked }))}
                    type="checkbox"
                  />
                  Item ativo
                </label>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Descrição</Label>
              <Textarea
                id="description"
                maxLength={1000}
                onChange={(event) => setValues((current) => ({ ...current, description: event.target.value }))}
                placeholder="Descrição opcional do item."
                value={values.description ?? ""}
              />
            </div>

            {error ? <FeedbackBanner message={error} variant="error" /> : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <Button onClick={onCancel} type="button" variant="outline">
                Cancelar
              </Button>
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? "Salvando..." : submitLabel}
              </Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
