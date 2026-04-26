import { useCallback, useEffect, useMemo, useState } from "react"
import { ArrowLeft } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/features/auth/use-auth"
import { ItemForm, type ItemFormValues } from "@/features/items/item-form"
import { createItem, getItem, updateItem } from "@/features/items/item-service"
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

  return "Não foi possível salvar o item."
}

export function ItemFormPage() {
  const navigate = useNavigate()
  const { itemId } = useParams()
  const { token } = useAuth()
  const isEditMode = Boolean(itemId)

  const [defaultValues, setDefaultValues] = useState<ItemFormValues | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [unitsError, setUnitsError] = useState<string | null>(null)
  const [units, setUnits] = useState<Unit[]>([])
  const [isLoading, setIsLoading] = useState(isEditMode)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [unitsLoading, setUnitsLoading] = useState(true)

  const activeUnitsCount = useMemo(() => units.filter((unit) => unit.is_active).length, [units])

  const loadDependencies = useCallback(async () => {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setUnitsError("Não foi possível identificar a sessão atual.")
      setIsLoading(false)
      setUnitsLoading(false)
      return
    }

    setError(null)
    setUnitsError(null)
    setUnitsLoading(true)
    if (isEditMode) {
      setIsLoading(true)
    }

    try {
      const unitsResponse = await listUnits(token)
      setUnits(unitsResponse.data)

      if (isEditMode && itemId) {
        const itemResponse = await getItem(token, itemId)
        setDefaultValues({
          name: itemResponse.data.name,
          item_type: itemResponse.data.item_type,
          unit_id: itemResponse.data.unit_id,
          description: itemResponse.data.description ?? "",
          minimum_stock: itemResponse.data.minimum_stock,
          is_active: itemResponse.data.is_active,
        })
      }
    } catch (requestError) {
      const message = getErrorMessage(requestError)
      if (isEditMode) {
        setError(message)
      } else {
        setUnitsError(message)
      }
    } finally {
      setUnitsLoading(false)
      setIsLoading(false)
    }
  }, [isEditMode, itemId, token])

  useEffect(() => {
    void loadDependencies()
  }, [loadDependencies])

  async function handleSubmit(values: ItemFormValues) {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      if (isEditMode && itemId) {
        await updateItem(token, itemId, values)
        navigate("/items", {
          replace: true,
          state: { message: "Item atualizado com sucesso.", tone: "success" },
        })
        return
      }

      await createItem(token, values)
      navigate("/items", {
        replace: true,
        state: { message: "Item criado com sucesso.", tone: "success" },
      })
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <Button asChild variant="outline">
            <Link to="/items">
              <ArrowLeft className="h-4 w-4" />
              Voltar para a lista
            </Link>
          </Button>
        }
        description={
          isEditMode
            ? "Atualize as informações do item selecionado."
            : "Cadastre um novo medicamento ou insumo."
        }
        title={isEditMode ? "Editar item" : "Novo item"}
      />

      {!isEditMode && !unitsLoading && activeUnitsCount === 0 ? (
        <FeedbackBanner
          message={
            <>
              Nenhuma unidade ativa disponível para vincular ao item. Cadastre uma unidade primeiro em{" "}
              <Link className="font-medium underline" to="/units/new">
                /units/new
              </Link>
              .
            </>
          }
          variant="warning"
        />
      ) : null}

      {isLoading ? (
        <div className="rounded-2xl border border-border/80 bg-white/92 px-6 py-10 text-sm text-muted-foreground">
          Carregando dados do item...
        </div>
      ) : isEditMode && !defaultValues ? (
        <FeedbackBanner message={error || "Não foi possível carregar os dados do item para edição."} variant="error" />
      ) : (
        <ItemForm
          defaultValues={defaultValues}
          description="Preencha os dados para identificar, organizar e acompanhar este item."
          error={error}
          isSubmitting={isSubmitting}
          onCancel={() => navigate("/items")}
          onSubmit={handleSubmit}
          submitLabel={isEditMode ? "Salvar alterações" : "Criar item"}
          title={isEditMode ? "Formulário de edição" : "Formulário de criação"}
          units={units}
          unitsError={unitsError}
          unitsLoading={unitsLoading}
        />
      )}
    </div>
  )
}
