import { LogOut, Menu } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useAuth } from "@/features/auth/use-auth"

interface HeaderProps {
  onMenuOpen: () => void
}

export function Header({ onMenuOpen }: HeaderProps) {
  const { signOut, user } = useAuth()

  return (
    <header className="rounded-3xl border border-border/70 bg-white/88 px-6 py-5 shadow-soft backdrop-blur">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button
            className="lg:hidden"
            onClick={onMenuOpen}
            size="icon"
            variant="ghost"
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Abrir menu</span>
          </Button>
          <div>
            <p className="text-sm font-medium text-primary">Casa Vida</p>
            <h1 className="text-2xl font-semibold tracking-tight">Painel administrativo</h1>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="hidden text-sm text-muted-foreground sm:block sm:text-right">
            <p className="font-medium text-foreground">{user?.full_name}</p>
            <p>{user?.email}</p>
          </div>
          <Button onClick={signOut} size="sm" variant="outline">
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Sair</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
