import { BellRing, ClipboardList, LayoutDashboard, LogOut, Package, Pill, Ruler, Users } from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/features/auth/use-auth"
import { cn } from "@/lib/utils"

const navigationItems = [
  { icon: LayoutDashboard, label: "Dashboard", to: "/dashboard" },
  { icon: Ruler, label: "Unidades", to: "/units" },
  { icon: Pill, label: "Itens", to: "/items" },
  { icon: Users, label: "Pacientes", to: "/patients" },
  { icon: ClipboardList, label: "Prescrições", to: "/prescriptions" },
  { icon: Package, label: "Estoque", to: "/inventory" },
  { icon: BellRing, label: "Alertas", to: "/alerts" },
]

export function AppLayout() {
  const { signOut, user } = useAuth()

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(15,118,110,0.14),_transparent_28%),linear-gradient(180deg,#f8faf8_0%,#f4f1e6_100%)] text-foreground">
      <div className="mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[248px_1fr] lg:px-6">
        <aside className="rounded-3xl border border-border/70 bg-white/88 p-4 shadow-soft backdrop-blur">
          <div className="mb-8 space-y-3">
            <Badge variant="outline">Casa Assistencial</Badge>
            <div>
              <p className="text-xl font-semibold">Painel administrativo</p>
              <p className="text-sm text-muted-foreground">
                Acompanhe pacientes, itens, prescrições, estoque e alertas em um so lugar.
              </p>
            </div>
          </div>

          <nav className="space-y-2">
            {navigationItems.map(({ icon: Icon, label, to }) => (
              <NavLink
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                  )
                }
                key={to}
                to={to}
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-8 rounded-2xl border border-border/70 bg-secondary/30 p-4 text-sm">
            <p className="font-medium text-foreground">Caminho sugerido</p>
            <p className="mt-2 text-muted-foreground">
              Comece por unidades e itens, siga para pacientes e prescrições, depois acompanhe estoque e alertas.
            </p>
          </div>
        </aside>

        <div className="flex min-h-full flex-col gap-6">
          <header className="rounded-3xl border border-border/70 bg-white/88 px-6 py-5 shadow-soft backdrop-blur">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm font-medium text-primary">Casa Assistencial</p>
                <h1 className="text-2xl font-semibold tracking-tight">Painel administrativo</h1>
              </div>
              <div className="flex flex-col gap-3 sm:items-end">
                <div className="text-sm text-muted-foreground sm:text-right">
                  <p className="font-medium text-foreground">{user?.full_name}</p>
                  <p>{user?.email}</p>
                </div>
                <Button onClick={signOut} size="sm" variant="outline">
                  <LogOut className="h-4 w-4" />
                  Sair
                </Button>
              </div>
            </div>
          </header>

          <main className="flex-1">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
