import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

type FeedbackBannerProps = {
  message: ReactNode
  title?: string
  variant?: "error" | "success" | "warning" | "info"
}

const variantClasses: Record<NonNullable<FeedbackBannerProps["variant"]>, string> = {
  error: "border-red-200 bg-red-50 text-red-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
}

export function FeedbackBanner({ message, title, variant = "info" }: FeedbackBannerProps) {
  return (
    <div className={cn("rounded-2xl border px-4 py-3 text-sm", variantClasses[variant])}>
      {title ? <p className="mb-1 font-medium">{title}</p> : null}
      <div>{message}</div>
    </div>
  )
}
