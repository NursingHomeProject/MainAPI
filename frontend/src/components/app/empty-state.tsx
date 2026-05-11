import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

type EmptyStateProps = {
  action?: ReactNode
  description: string
  icon: LucideIcon
  title: string
}

export function EmptyState({ action, description, icon: Icon, title }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 py-12 text-center">
      <div className="rounded-full bg-secondary p-4 text-primary">
        <Icon className="h-6 w-6" />
      </div>
      <div className="space-y-1">
        <p className="text-lg font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {action}
    </div>
  )
}
