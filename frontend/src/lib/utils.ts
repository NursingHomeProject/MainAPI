import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDecimalAsInteger(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return ""
  }

  const normalizedValue = typeof value === "string" ? value.replace(",", ".") : value
  const numericValue = Number(normalizedValue)

  if (Number.isNaN(numericValue)) {
    return String(value)
  }

  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 0,
  }).format(Math.trunc(numericValue))
}

export function formatSignedDecimalAsInteger(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return ""
  }

  const normalizedValue = typeof value === "string" ? value.replace(",", ".") : value
  const numericValue = Number(normalizedValue)

  if (Number.isNaN(numericValue)) {
    return String(value)
  }

  const prefix = numericValue > 0 ? "+" : ""
  return `${prefix}${formatDecimalAsInteger(numericValue)}`
}

function formatOperationalTextToken(token: string) {
  const normalizedValue = token.replace(",", ".")
  const numericValue = Number(normalizedValue)

  if (Number.isNaN(numericValue)) {
    return token
  }

  const fractionMatch = token.match(/[.,](\d+)$/)
  const fractionDigits = fractionMatch?.[1]?.length ?? 0

  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: Math.min(fractionDigits, 3),
  }).format(numericValue)
}

export function formatOperationalTextNumbers(text: string | null | undefined) {
  if (!text) {
    return ""
  }

  return text.replace(/[+-]?\d+(?:[.,]\d+)?/g, (token, offset, sourceText) => {
    const previousCharacter = sourceText[offset - 1] ?? ""
    const nextCharacter = sourceText[offset + token.length] ?? ""
    const beforePreviousCharacter = sourceText[offset - 2] ?? ""
    const afterNextCharacter = sourceText[offset + token.length + 1] ?? ""

    const looksLikeTime = previousCharacter === ":" || nextCharacter === ":"
    const looksLikeDate =
      (previousCharacter === "-" && /\d/.test(beforePreviousCharacter)) ||
      (nextCharacter === "-" && /\d/.test(afterNextCharacter)) ||
      previousCharacter === "/" ||
      nextCharacter === "/"

    if (looksLikeTime || looksLikeDate) {
      return token
    }

    return formatOperationalTextToken(token)
  })
}
