import { BellRing, ClipboardList, LayoutDashboard, Package, Pill, Ruler, Users } from "lucide-react"
import { NavLink } from "react-router-dom"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export const navigationItems = [
  { icon: LayoutDashboard, label: "Dashboard", to: "/dashboard" },
  { icon: Ruler, label: "Unidades", to: "/units" },
  { icon: Pill, label: "Itens", to: "/items" },
  { icon: Users, label: "Pacientes", to: "/patients" },
  { icon: ClipboardList, label: "Prescrições", to: "/prescriptions" },
  { icon: Package, label: "Estoque", to: "/inventory" },
  { icon: BellRing, label: "Alertas", to: "/alerts" },
]

interface SidebarContentProps {
  onNavigate?: () => void
}

export function SidebarContent({ onNavigate }: SidebarContentProps) {
  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-8 space-y-3">
        <Badge variant="outline">Casa Vida</Badge>
        <div>
          <p className="text-xl font-semibold">Painel administrativo</p>
          <p className="text-sm text-muted-foreground">
            Acompanhe pacientes, itens, prescrições, estoque e alertas em um só lugar.
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
            onClick={onNavigate}
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
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="hidden rounded-3xl border border-border/70 bg-white/88 shadow-soft backdrop-blur lg:block">
      <SidebarContent />
    </aside>
  )
}
