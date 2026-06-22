/*
 * ============================================================
 * CHECKLIST DE VALIDAÇÃO MANUAL — StockEntryModal
 * ============================================================
 * [ ] Abrir detalhe de paciente com prescrições ativas
 * [ ] Rolar até a seção "Estoque por medicamento"
 * [ ] Verificar card resumo: se algum item estiver abaixo do mínimo,
 *     deve aparecer banner amarelo com contagem ("X medicamento(s) abaixo...")
 * [ ] Clicar "Registrar entrada" em qualquer item → modal deve abrir
 *     com o título "Registrar entrada" e o nome do item na descrição
 * [ ] Tentar clicar "Confirmar entrada" sem preencher quantidade →
 *     botão deve estar desabilitado
 * [ ] Preencher quantidade e confirmar → saldo do item deve atualizar
 *     sem recarregar a página inteira
 * [ ] Preencher observação opcional → deve ser salva junto da movimentação
 * [ ] Preencher data retroativa e confirmar → movimentação deve usar a data informada
 * [ ] Clicar "Ver histórico" → lista de movimentações expande abaixo do card
 * [ ] Testar com paciente sem prescrições ativas → seção deve mostrar
 *     "Nenhum medicamento com estoque"
 * [ ] Testar dois pacientes com o mesmo medicamento → cada um deve ter
 *     saldo e histórico independentes
 * ============================================================
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { PatientItemStock } from "@/types/inventory"
import { StockEntryModal } from "../stock-entry-modal"

// ── Mock do serviço de inventário ──────────────────────────────────────────
vi.mock("@/features/inventory/inventory-service", () => ({
  createPatientStockEntry: vi.fn(),
}))

// Importa APÓS o vi.mock para obter a versão mockada
import { createPatientStockEntry } from "@/features/inventory/inventory-service"
const mockCreate = vi.mocked(createPatientStockEntry)

// ── Fixtures ───────────────────────────────────────────────────────────────
const FAKE_ITEM: PatientItemStock = {
  item_id: "item-uuid-1",
  item_name: "Dipirona 500mg",
  unit_symbol: "comprimido",
  current_stock: "18",
  minimum_stock: "5",
  is_below_minimum: false,
  total_daily_dose: "3",
  estimated_days_remaining: "6",
  prescription_ids: ["presc-uuid-1"],
}

function renderModal(overrides: Partial<Parameters<typeof StockEntryModal>[0]> = {}) {
  const props = {
    open: true,
    onOpenChange: vi.fn(),
    patientId: "patient-uuid-1",
    item: FAKE_ITEM,
    token: "fake-token",
    onSuccess: vi.fn(),
    ...overrides,
  }
  return { ...render(<StockEntryModal {...props} />), props }
}

// ── Testes ─────────────────────────────────────────────────────────────────
describe("StockEntryModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // 1 — renderiza com nome do item no título
  it("renderiza o título e o nome do item na descrição", () => {
    renderModal()

    expect(screen.getByText("Registrar entrada")).toBeInTheDocument()
    expect(screen.getByText(/Dipirona 500mg/)).toBeInTheDocument()
  })

  // 2 — botão desabilitado com quantity vazia
  it("desabilita o botão Confirmar quando a quantidade está vazia", () => {
    renderModal()

    const confirmBtn = screen.getByRole("button", { name: /confirmar entrada/i })
    expect(confirmBtn).toBeDisabled()
  })

  // 3 — chama createPatientStockEntry com os valores corretos
  it("chama createPatientStockEntry com os dados preenchidos ao confirmar", async () => {
    mockCreate.mockResolvedValue({} as never)
    const user = userEvent.setup()
    renderModal()

    // Preenche quantidade (input type=number → role="spinbutton")
    const quantityInput = screen.getByRole("spinbutton")
    await user.clear(quantityInput)
    await user.type(quantityInput, "30")

    await user.click(screen.getByRole("button", { name: /confirmar entrada/i }))

    expect(mockCreate).toHaveBeenCalledOnce()
    expect(mockCreate).toHaveBeenCalledWith("fake-token", "patient-uuid-1", {
      item_id: "item-uuid-1",
      quantity: "30",
      notes: null,
      occurred_at: null,
    })
  })

  // 4 — loading state durante o envio
  it("mostra Salvando... e desabilita o botão durante o envio", async () => {
    // Promise que nunca resolve → trava na etapa de loading
    mockCreate.mockImplementation(() => new Promise(() => {}))
    const user = userEvent.setup()
    renderModal()

    await user.type(screen.getByRole("spinbutton"), "30")
    await user.click(screen.getByRole("button", { name: /confirmar entrada/i }))

    // Botão deve mostrar loading
    const loadingBtn = screen.getByRole("button", { name: /salvando/i })
    expect(loadingBtn).toBeInTheDocument()
    expect(loadingBtn).toBeDisabled()
  })

  // 5 — chama onSuccess e fecha o modal após sucesso
  it("chama onSuccess e onOpenChange(false) após envio bem-sucedido", async () => {
    mockCreate.mockResolvedValue({} as never)
    const onSuccess = vi.fn()
    const onOpenChange = vi.fn()
    const user = userEvent.setup()
    renderModal({ onSuccess, onOpenChange })

    await user.type(screen.getByRole("spinbutton"), "30")
    await user.click(screen.getByRole("button", { name: /confirmar entrada/i }))

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledOnce()
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })

  // 6 — mostra FeedbackBanner em caso de erro da API
  it("exibe mensagem de erro quando a API retorna falha", async () => {
    mockCreate.mockRejectedValue(new Error("Servidor indisponível"))
    const user = userEvent.setup()
    renderModal()

    await user.type(screen.getByRole("spinbutton"), "30")
    await user.click(screen.getByRole("button", { name: /confirmar entrada/i }))

    await waitFor(() => {
      expect(screen.getByText("Servidor indisponível")).toBeInTheDocument()
    })

    // Confirmar ainda deve estar presente (não fechou o modal)
    expect(screen.getByRole("button", { name: /confirmar entrada/i })).toBeInTheDocument()
  })
})
