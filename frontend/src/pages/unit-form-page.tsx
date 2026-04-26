import { useCallback, useEffect, useState } from "react"
import { ArrowLeft } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/features/auth/use-auth"
import { UnitForm, type UnitFormValues } from "@/features/units/unit-form"
import { createUnit, getUnit, updateUnit } from "@/features/units/unit-service"
import { HttpError } from "@/services/http"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível salvar a unidade."
}

export function UnitFormPage() {
  const navigate = useNavigate()
  const { unitId } = useParams()
  const { token } = useAuth()
  const isEditMode = Boolean(unitId)

  const [defaultValues, setDefaultValues] = useState<UnitFormValues | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(isEditMode)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadUnit = useCallback(async () => {
    if (!isEditMode || !unitId) {
      return
    }

    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await getUnit(token, unitId)
      setDefaultValues({
        name: response.data.name,
        symbol: response.data.symbol,
        description: response.data.description ?? "",
        is_active: response.data.is_active,
      })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [isEditMode, token, unitId])

  useEffect(() => {
    void loadUnit()
  }, [loadUnit])

  async function handleSubmit(values: UnitFormValues) {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      if (isEditMode && unitId) {
        await updateUnit(token, unitId, values)
        navigate("/units", {
          replace: true,
          state: { message: "Unidade atualizada com sucesso.", tone: "success" },
        })
        return
      }

      await createUnit(token, values)
      navigate("/units", {
        replace: true,
        state: { message: "Unidade criada com sucesso.", tone: "success" },
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
            <Link to="/units">
              <ArrowLeft className="h-4 w-4" />
              Voltar para a lista
            </Link>
          </Button>
        }
        description={
          isEditMode
            ? "Atualize os dados da unidade selecionada."
            : "Cadastre uma nova unidade de medida."
        }
        title={isEditMode ? "Editar unidade" : "Nova unidade"}
      />

      {isLoading ? (
        <div className="rounded-2xl border border-border/80 bg-white/92 px-6 py-10 text-sm text-muted-foreground">
          Carregando dados da unidade...
        </div>
      ) : isEditMode && !defaultValues ? (
        <FeedbackBanner
          message={error || "Não foi possível carregar os dados da unidade para edição."}
          variant="error"
        />
      ) : (
        <UnitForm
          defaultValues={defaultValues}
          description="Preencha os dados para identificar como essa unidade sera usada no sistema."
          error={error}
          isSubmitting={isSubmitting}
          onCancel={() => navigate("/units")}
          onSubmit={handleSubmit}
          submitLabel={isEditMode ? "Salvar alterações" : "Criar unidade"}
          title={isEditMode ? "Formulário de edição" : "Formulário de criação"}
        />
      )}
    </div>
  )
}
