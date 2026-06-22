/*
 * ============================================================
 * CHECKLIST DE VALIDAÇÃO MANUAL — AdministrationModal
 * ============================================================
 * [ ] Abrir detalhe de paciente com prescrições ativas e estoque cadastrado
 * [ ] Clicar "Registrar administração" em qualquer medicamento → modal abre com:
 *     - Título "Registrar administração"
 *     - Nome do medicamento no subtítulo
 *     - Campo de dose pré-preenchido com a dose prescrita (editável)
 *     - Texto de rodapé: "O horário de administração é registrado automaticamente..."
 * [ ] Confirmar sem alterar a dose → dose prescrita deve ser registrada
 * [ ] Alterar a dose para um valor diferente e confirmar → novo valor deve ser registrado
 * [ ] Tentar confirmar com campo de dose vazio → botão deve estar desabilitado
 * [ ] Clicar "Confirmar administração" → no DevTools/Network, verificar que o JSON enviado
 *     NÃO contém nenhuma propriedade "occurred_at" (anti-fraude crítico)
 * [ ] Após confirmação bem-sucedida: saldo do item atualiza E agenda de doses atualiza
 * [ ] Verificar na seção "Agenda de doses do dia": dose aparece como "concluída" (estado completed)
 * [ ] Testar com medicamento com estoque abaixo do mínimo → banner de aviso deve aparecer
 * [ ] Testar erro de rede → mensagem de erro deve aparecer no modal sem fechá-lo
 * ============================================================
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { PatientItemStock } from "@/types/inventory"
import { AdministrationModal } from "../administration-modal"

// ── Mock do serviço — deve vir ANTES do import do módulo mockado ──────────
vi.mock("@/features/inventory/inventory-service", () => ({
  registerDoseAdministration: vi.fn(),
}))

// Importa APÓS o vi.mock para obter a versão mockada
import { registerDoseAdministration } from "@/features/inventory/inventory-service"
const mockRegister = vi.mocked(registerDoseAdministration)

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

const FAKE_ITEM_BELOW_MINIMUM: PatientItemStock = {
  ...FAKE_ITEM,
  item_id: "item-uuid-2",
  item_name: "Insulina NPH",
  current_stock: "2",
  minimum_stock: "10",
  is_below_minimum: true,
}

function renderModal(overrides: Partial<Parameters<typeof AdministrationModal>[0]> = {}) {
  const props = {
    open: true,
    onOpenChange: vi.fn(),
    patientId: "patient-uuid-1",
    item: FAKE_ITEM,
    doseAmount: "1",
    token: "fake-token",
    onSuccess: vi.fn(),
    ...overrides,
  }
  return { ...render(<AdministrationModal {...props} />), props }
}

// ── Testes ─────────────────────────────────────────────────────────────────
describe("AdministrationModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // 1 — renderização básica com dose pré-preenchida
  it("renderiza título, nome do medicamento e campo de dose pré-preenchido", async () => {
    renderModal()

    expect(screen.getByText("Registrar administração")).toBeInTheDocument()
    expect(screen.getByText("Dipirona 500mg")).toBeInTheDocument()
    // useEffect pré-preenche o campo com doseAmount="1"; waitFor garante
    // que o efeito foi processado antes da assertion
    await waitFor(() => {
      expect(screen.getByRole("spinbutton")).toHaveValue(1)
    })
  })

  // 2 — rodapé anti-fraude: sem nenhum campo de data/hora
  it("exibe texto de horário automático e não renderiza nenhum campo de data/hora", () => {
    renderModal()

    expect(screen.getByText(/registrado automaticamente/i)).toBeInTheDocument()
    // CRÍTICO: nenhum input de data/hora deve existir no DOM
    expect(document.querySelector('input[type="datetime-local"]')).toBeNull()
    expect(document.querySelector('input[type="time"]')).toBeNull()
    expect(document.querySelector('input[type="date"]')).toBeNull()
  })

  // 3 — botão desabilitado quando campo de dose está vazio
  it("desabilita o botão Confirmar quando o campo de dose está vazio", async () => {
    const user = userEvent.setup()
    renderModal()

    // Limpa o campo pré-preenchido pelo useEffect
    await user.clear(screen.getByRole("spinbutton"))

    expect(
      screen.getByRole("button", { name: /confirmar administração/i }),
    ).toBeDisabled()
  })

  // 4 — ANTI-FRAUDE (crítico): occurred_at nunca aparece no payload
  it("chama registerDoseAdministration sem o campo occurred_at no payload", async () => {
    mockRegister.mockResolvedValue({} as never)
    const user = userEvent.setup()
    renderModal()

    const input = screen.getByRole("spinbutton")
    await user.clear(input)
    await user.type(input, "2")
    await user.click(screen.getByRole("button", { name: /confirmar administração/i }))

    await waitFor(() => expect(mockRegister).toHaveBeenCalledOnce())

    // Verifica os argumentos posicionais: token, patientId, payload
    expect(mockRegister).toHaveBeenCalledWith(
      "fake-token",
      "patient-uuid-1",
      expect.objectContaining({
        item_id: "item-uuid-1",
        quantity: "2",
      }),
    )

    // Verificação explícita anti-fraude: occurred_at NÃO deve existir no payload
    const payload = mockRegister.mock.calls[0][2]
    expect(payload).not.toHaveProperty("occurred_at")
  })

  // 5 — usa dose pré-preenchida sem modificação
  it("envia o doseAmount como quantity quando o campo não é alterado", async () => {
    mockRegister.mockResolvedValue({} as never)
    const user = userEvent.setup()
    // Renderiza com doseAmount="3"; useEffect pré-preenche o campo
    renderModal({ doseAmount: "3" })

    // Clica confirmar diretamente — sem alterar o campo
    await user.click(screen.getByRole("button", { name: /confirmar administração/i }))

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith(
        "fake-token",
        "patient-uuid-1",
        expect.objectContaining({ quantity: "3" }),
      )
    })
  })

  // 6 — loading state durante o envio
  it("mostra Salvando... e desabilita o botão durante o envio", async () => {
    // Promise que nunca resolve → estado de loading permanente
    mockRegister.mockImplementation(() => new Promise(() => {}))
    const user = userEvent.setup()
    renderModal()

    // Campo já tem valor "1" pelo useEffect — botão habilitado
    await user.click(screen.getByRole("button", { name: /confirmar administração/i }))

    // Após o clique, React re-renderiza com loading=true
    const loadingBtn = screen.getByRole("button", { name: /salvando/i })
    expect(loadingBtn).toBeInTheDocument()
    expect(loadingBtn).toBeDisabled()
  })

  // 7 — onSuccess e fechamento após confirmação bem-sucedida
  it("chama onSuccess e onOpenChange(false) após confirmação bem-sucedida", async () => {
    mockRegister.mockResolvedValue({} as never)
    const onSuccess = vi.fn()
    const onOpenChange = vi.fn()
    const user = userEvent.setup()
    renderModal({ onSuccess, onOpenChange })

    // Campo pré-preenchido com "1" — confirma diretamente
    await user.click(screen.getByRole("button", { name: /confirmar administração/i }))

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledOnce()
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })

  // 8 — erro da API exibido sem fechar o modal
  it("exibe mensagem de erro quando a API retorna falha sem fechar o modal", async () => {
    mockRegister.mockRejectedValue(new Error("Estoque insuficiente"))
    const user = userEvent.setup()
    renderModal()

    await user.click(screen.getByRole("button", { name: /confirmar administração/i }))

    await waitFor(() => {
      expect(screen.getByText("Estoque insuficiente")).toBeInTheDocument()
    })

    // Modal não fechou — botão de confirmação ainda está presente
    expect(
      screen.getByRole("button", { name: /confirmar administração/i }),
    ).toBeInTheDocument()
  })

  // 9 — aviso de estoque abaixo do mínimo
  it("exibe banner de aviso quando is_below_minimum é true", () => {
    renderModal({ item: FAKE_ITEM_BELOW_MINIMUM })

    expect(screen.getByText(/estoque abaixo do mínimo/i)).toBeInTheDocument()
  })

  // 10 — não fecha durante loading (Cancelar desabilitado)
  it("não chama onOpenChange ao tentar cancelar enquanto o envio está em andamento", async () => {
    // Promise que nunca resolve → loading permanente
    mockRegister.mockImplementation(() => new Promise(() => {}))
    const onOpenChange = vi.fn()
    const user = userEvent.setup()
    renderModal({ onOpenChange })

    // Dispara o submit — ficará em loading eternamente
    await user.click(screen.getByRole("button", { name: /confirmar administração/i }))

    // Com loading=true, o botão Cancelar deve estar desabilitado
    const cancelBtn = screen.getByRole("button", { name: /cancelar/i })
    expect(cancelBtn).toBeDisabled()

    // onOpenChange não deve ter sido chamado em nenhum momento
    expect(onOpenChange).not.toHaveBeenCalled()
  })
})
