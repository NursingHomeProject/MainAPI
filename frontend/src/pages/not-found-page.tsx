import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-xl bg-white/92">
        <CardHeader>
          <CardTitle>Pagina não encontrada</CardTitle>
          <CardDescription>A pagina que voce tentou acessar não foi encontrada.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to="/">Voltar para a base do painel</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
