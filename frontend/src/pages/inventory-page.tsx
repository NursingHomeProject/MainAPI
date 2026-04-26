import { useCallback, useEffect, useMemo, useState } from "react"
import { ArrowDownUp, PackageSearch, RefreshCw } from "lucide-react"

import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { NativeSelect } from "@/components/app/native-select"
import { PageHeader } from "@/components/app/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { InventoryMovementForm, type InventoryMovementFormValues } from "@/features/inventory/inventory-movement-form"
import {
  createInventoryMovement,
  getItemStock,
  listInventoryMovements,
} from "@/features/inventory/inventory-service"
import { useAuth } from "@/features/auth/use-auth"
import { listItems } from "@/features/items/item-service"
import { listPatients } from "@/features/patients/patient-service"
import { formatDecimalAsInteger } from "@/lib/utils"
import { HttpError } from "@/services/http"
import type { InventoryMovement, InventoryMovementType, ItemStock } from "@/types/inventory"
import type { Item } from "@/types/item"
import type { Patient } from "@/types/patient"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível concluir a operação de estoque."
}

function getMovementTypeLabel(movementType: InventoryMovementType) {
  switch (movementType) {
    case "entry":
      return "Entrada"
    case "administration":
      return "Administração"
    case "loss":
      return "Perda"
    case "adjustment":
      return "Ajuste"
    case "discard":
      return "Descarte"
  }
}

function getItemTypeLabel(itemType: Item["item_type"]) {
  return itemType === "medication" ? "Medicamento" : "Insumo"
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
}

function formatStockEffect(value: string) {
  const formattedValue = formatDecimalAsInteger(value)

  if (value.startsWith("-")) {
    return formattedValue
  }

  return `+${formattedValue}`
}

export function InventoryPage() {
  const { token } = useAuth()

  const [items, setItems] = useState<Item[]>([])
  const [patients, setPatients] = useState<Patient[]>([])
  const [movements, setMovements] = useState<InventoryMovement[]>([])
  const [stockSummary, setStockSummary] = useState<ItemStock | null>(null)
  const [stockItemId, setStockItemId] = useState("")
  const [historyItemId, setHistoryItemId] = useState("")
  const [historyPatientId, setHistoryPatientId] = useState("")
  const [historyMovementType, setHistoryMovementType] = useState<InventoryMovementType | "">("")
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [stockError, setStockError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isDependenciesLoading, setIsDependenciesLoading] = useState(true)
  const [isHistoryLoading, setIsHistoryLoading] = useState(true)
  const [isStockLoading, setIsStockLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const itemMap = useMemo(() => new Map(items.map((item) => [item.id, item])), [items])
  const patientMap = useMemo(() => new Map(patients.map((patient) => [patient.id, patient])), [patients])

  const loadDependencies = useCallback(async () => {
    if (!token) {
      setItems([])
      setPatients([])
      setIsDependenciesLoading(false)
      setHistoryError("Não foi possível identificar a sessão atual.")
      return
    }

    setIsDependenciesLoading(true)

    try {
      const [itemsResponse, patientsResponse] = await Promise.all([listItems(token), listPatients(token)])
      setItems(itemsResponse.data)
      setPatients(patientsResponse.data)
    } catch (requestError) {
      setItems([])
      setPatients([])
      setHistoryError(getErrorMessage(requestError))
    } finally {
      setIsDependenciesLoading(false)
    }
  }, [token])

  const loadMovements = useCallback(async () => {
    if (!token) {
      setMovements([])
      setIsHistoryLoading(false)
      setHistoryError("Não foi possível identificar a sessão atual.")
      return
    }

    setIsHistoryLoading(true)
    setHistoryError(null)

    try {
      const response = await listInventoryMovements(token, {
        item_id: historyItemId || undefined,
        patient_id: historyPatientId || undefined,
        movement_type: historyMovementType || undefined,
      })
      setMovements(response.data)
    } catch (requestError) {
      setMovements([])
      setHistoryError(getErrorMessage(requestError))
    } finally {
      setIsHistoryLoading(false)
    }
  }, [historyItemId, historyMovementType, historyPatientId, token])

  const loadStockSummary = useCallback(async () => {
    if (!token || !stockItemId) {
      setStockSummary(null)
      setStockError(null)
      setIsStockLoading(false)
      return
    }

    setIsStockLoading(true)
    setStockError(null)

    try {
      const response = await getItemStock(token, stockItemId)
      setStockSummary(response.data)
    } catch (requestError) {
      setStockSummary(null)
      setStockError(getErrorMessage(requestError))
    } finally {
      setIsStockLoading(false)
    }
  }, [stockItemId, token])

  useEffect(() => {
    void loadDependencies()
  }, [loadDependencies])

  useEffect(() => {
    void loadMovements()
  }, [loadMovements])

  useEffect(() => {
    void loadStockSummary()
  }, [loadStockSummary])

  async function handleSubmit(values: InventoryMovementFormValues) {
    if (!token) {
      setSubmitError("Não foi possível identificar a sessão atual.")
      return
    }

    setIsSubmitting(true)
    setSubmitError(null)
    setSuccessMessage(null)

    try {
      const response = await createInventoryMovement(token, values)
      const nextItemId = response.data.item_id
      const nextPatientId = response.data.patient_id ?? ""
      const [updatedMovements, updatedStock] = await Promise.all([
        listInventoryMovements(token, {
          item_id: nextItemId,
          patient_id: nextPatientId || undefined,
        }),
        getItemStock(token, nextItemId),
      ])

      setSuccessMessage("Movimentacao registrada com sucesso.")
      setHistoryError(null)
      setMovements(updatedMovements.data)
      setHistoryItemId(nextItemId)
      setHistoryPatientId(nextPatientId)
      setHistoryMovementType("")
      setStockError(null)
      setStockSummary(updatedStock.data)
      setStockItemId(nextItemId)
    } catch (requestError) {
      setSubmitError(getErrorMessage(requestError))
    } finally {
      setIsSubmitting(false)
    }
  }

  const historyHasFilters = Boolean(historyItemId || historyPatientId || historyMovementType)

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <Button
            onClick={() => {
              void loadDependencies()
              void loadMovements()
              void loadStockSummary()
            }}
            variant="outline"
          >
            <RefreshCw className="h-4 w-4" />
            Atualizar tudo
          </Button>
        }
        description="Acompanhe saldos, registre movimentacoes e consulte o histórico dos itens."
        title="Estoque e movimentacoes"
      />

      {successMessage ? <FeedbackBanner message={successMessage} variant="success" /> : null}

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="bg-white/92">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PackageSearch className="h-4 w-4 text-primary" />
              Saldo por item
            </CardTitle>
            <CardDescription>Consulte o saldo atual e o estoque minimo de cada item.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="stock-item-filter">
                Item
              </label>
              <NativeSelect
                id="stock-item-filter"
                onChange={(event) => setStockItemId(event.target.value)}
                value={stockItemId}
              >
                <option value="">Selecione um item para consultar saldo</option>
                {items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                    {item.is_active ? "" : " - inativo"}
                  </option>
                ))}
              </NativeSelect>
            </div>

            {stockError ? <FeedbackBanner message={stockError} variant="error" /> : null}

            {isStockLoading ? (
              <div className="rounded-2xl border border-border/80 bg-secondary/20 px-4 py-6 text-sm text-muted-foreground">
                Carregando saldo do item...
              </div>
            ) : null}

            {!isStockLoading && !stockItemId ? (
              <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                <EmptyState
                  description="Escolha um item para visualizar o saldo atual."
                  icon={PackageSearch}
                  title="Selecione um item"
                />
              </div>
            ) : null}

            {stockSummary ? (
              <div className="grid gap-3">
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{stockSummary.item_name}</p>
                      <p className="text-sm text-muted-foreground">{getItemTypeLabel(stockSummary.item_type)}</p>
                    </div>
                    <Badge variant={stockSummary.is_below_minimum ? "warning" : "success"}>
                      {stockSummary.is_below_minimum ? "Abaixo do minimo" : "Saldo ok"}
                    </Badge>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-sm text-muted-foreground">Saldo atual</p>
                      <p className="text-2xl font-semibold">
                        {formatDecimalAsInteger(stockSummary.current_stock)} {stockSummary.unit_symbol}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Estoque minimo</p>
                      <p className="text-2xl font-semibold">
                        {formatDecimalAsInteger(stockSummary.minimum_stock)} {stockSummary.unit_symbol}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <InventoryMovementForm
          key={stockItemId || "inventory-form"}
          defaultItemId={stockItemId}
          error={submitError}
          isSubmitting={isSubmitting}
          items={items}
          itemsLoading={isDependenciesLoading}
          onSubmit={handleSubmit}
          patients={patients}
          patientsLoading={isDependenciesLoading}
        />
      </section>

      <Card className="bg-white/92">
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ArrowDownUp className="h-4 w-4 text-primary" />
              Histórico de movimentacoes
            </CardTitle>
            <CardDescription>Veja as movimentacoes registradas e use os filtros para encontrar o que precisa.</CardDescription>
          </div>
          <Button onClick={() => void loadMovements()} variant="outline">
            <RefreshCw className="h-4 w-4" />
            Atualizar histórico
          </Button>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="history-item-filter">
                Filtrar por item
              </label>
              <NativeSelect
                id="history-item-filter"
                onChange={(event) => setHistoryItemId(event.target.value)}
                value={historyItemId}
              >
                <option value="">Todos os itens</option>
                {items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </NativeSelect>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="history-patient-filter">
                Filtrar por paciente
              </label>
              <NativeSelect
                id="history-patient-filter"
                onChange={(event) => setHistoryPatientId(event.target.value)}
                value={historyPatientId}
              >
                <option value="">Todos os pacientes</option>
                {patients.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {patient.full_name}
                  </option>
                ))}
              </NativeSelect>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="history-type-filter">
                Filtrar por tipo
              </label>
              <NativeSelect
                id="history-type-filter"
                onChange={(event) => setHistoryMovementType((event.target.value as InventoryMovementType | "") || "")}
                value={historyMovementType}
              >
                <option value="">Todos os tipos</option>
                <option value="entry">Entrada</option>
                <option value="administration">Administração</option>
                <option value="loss">Perda</option>
                <option value="adjustment">Ajuste</option>
                <option value="discard">Descarte</option>
              </NativeSelect>
            </div>
          </div>

          {historyHasFilters ? (
            <FeedbackBanner
              message="Filtros ativos para facilitar a consulta das movimentacoes."
              variant="info"
            />
          ) : null}

          {historyError ? <FeedbackBanner message={historyError} variant="error" /> : null}

          {isHistoryLoading ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {Array.from({ length: 2 }).map((_, index) => (
                <Card className="bg-secondary/20" key={index}>
                  <CardContent className="grid gap-3 py-6">
                    <div className="h-5 w-40 animate-pulse rounded bg-secondary" />
                    <div className="h-4 w-full animate-pulse rounded bg-secondary" />
                    <div className="h-4 w-3/4 animate-pulse rounded bg-secondary" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : null}

          {!isHistoryLoading && movements.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
              <EmptyState
                description="Ajuste os filtros ou registre uma nova movimentacao para preencher o histórico."
                icon={ArrowDownUp}
                title="Nenhuma movimentacao encontrada"
              />
            </div>
          ) : null}

          {!isHistoryLoading ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {movements.map((movement) => {
                const item = itemMap.get(movement.item_id)
                const patient = movement.patient_id ? patientMap.get(movement.patient_id) : null

                return (
                  <Card className="bg-secondary/15" key={movement.id}>
                    <CardContent className="space-y-4 py-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-medium text-foreground">{item?.name ?? movement.item_id}</p>
                          <p className="text-sm text-muted-foreground">
                            {getMovementTypeLabel(movement.movement_type)}
                            {movement.adjustment_operation ? ` | ${movement.adjustment_operation}` : ""}
                          </p>
                        </div>
                        <Badge variant={movement.stock_effect.startsWith("-") ? "warning" : "success"}>
                          {formatStockEffect(movement.stock_effect)}
                        </Badge>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2 text-sm">
                        <div>
                          <p className="text-muted-foreground">Quantidade</p>
                          <p className="font-medium">{formatDecimalAsInteger(movement.quantity)}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Paciente</p>
                          <p className="font-medium">{patient?.full_name ?? "Não informado"}</p>
                        </div>
                      </div>

                      <div>
                        <p className="text-sm text-muted-foreground">Notas</p>
                        <p className="text-sm font-medium text-foreground">
                          {movement.notes?.trim() || "Sem notas informadas."}
                        </p>
                      </div>

                      <p className="text-xs text-muted-foreground">{formatDateTime(movement.occurred_at)}</p>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
