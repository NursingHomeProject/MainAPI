import { useState } from "react"
import { Outlet } from "react-router-dom"

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Header } from "@/layouts/header"
import { Sidebar, SidebarContent } from "@/layouts/sidebar"

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(15,118,110,0.14),_transparent_28%),linear-gradient(180deg,#f8faf8_0%,#f4f1e6_100%)] text-foreground">
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent className="w-72 p-0" side="left">
          <SheetHeader className="sr-only">
            <SheetTitle>Menu de navegação</SheetTitle>
            <SheetDescription>Navegue pelas seções do painel administrativo.</SheetDescription>
          </SheetHeader>
          <SidebarContent onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[248px_1fr] lg:px-6">
        <Sidebar />

        <div className="flex min-h-full flex-col gap-6">
          <Header onMenuOpen={() => setMobileOpen(true)} />

          <main className="flex-1">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
