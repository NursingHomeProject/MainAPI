export type ApiEnvelope<T> = {
  data: T
}

export type ApiListEnvelope<T> = {
  data: T[]
  total: number
}

export type ApiErrorResponse = {
  detail?: string
  message?: string
}
