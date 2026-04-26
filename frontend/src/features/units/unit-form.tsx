import { type FormEvent, useState } from "react"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { UnitCreatePayload } from "@/types/unit"

export type UnitFormValues = UnitCreatePayload

type UnitFormProps = {
  defaultValues?: UnitFormValues
  description: string
  error: string | null
  isSubmitting: boolean
  submitLabel: string
  title: string
  onCancel: () => void
  onSubmit: (values: UnitFormValues) => Promise<void>
}

const defaultUnitValues: UnitFormValues = {
  name: "",
  symbol: "",
  description: "",
  is_active: true,
}

export function UnitForm({
  defaultValues,
  description,
  error,
  isSubmitting,
  onCancel,
  onSubmit,
  submitLabel,
  title,
}: UnitFormProps) {
  const [values, setValues] = useState<UnitFormValues>(defaultValues ?? defaultUnitValues)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      name: values.name,
      symbol: values.symbol,
      description: values.description?.trim() ? values.description.trim() : null,
      is_active: values.is_active,
    })
  }

  return (
    <Card className="bg-white/92">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="grid gap-5 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Nome</Label>
              <Input
                id="name"
                maxLength={100}
                onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))}
                placeholder="Ex.: mililitro"
                required
                value={values.name}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="symbol">Símbolo</Label>
              <Input
                id="symbol"
                maxLength={20}
                onChange={(event) => setValues((current) => ({ ...current, symbol: event.target.value }))}
                placeholder="Ex.: ml"
                required
                value={values.symbol}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Descrição</Label>
            <Textarea
              id="description"
              maxLength={500}
              onChange={(event) => setValues((current) => ({ ...current, description: event.target.value }))}
              placeholder="Descrição opcional da unidade."
              value={values.description ?? ""}
            />
          </div>

          <label className="flex items-center gap-3 rounded-xl border border-border/70 bg-secondary/30 px-4 py-3 text-sm">
            <input
              checked={values.is_active}
              className="h-4 w-4 accent-hsl(var(--primary))"
              onChange={(event) => setValues((current) => ({ ...current, is_active: event.target.checked }))}
              type="checkbox"
            />
            Unidade ativa
          </label>

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
      </CardContent>
    </Card>
  )
}
