import { env } from "@/config/env"
import type { ApiErrorResponse } from "@/types/api"

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"

type RequestOptions = {
  body?: BodyInit | null
  headers?: HeadersInit
  method?: HttpMethod
  signal?: AbortSignal
}

export class HttpError extends Error {
  readonly status: number
  readonly payload?: ApiErrorResponse

  constructor(message: string, status: number, payload?: ApiErrorResponse) {
    super(message)
    this.name = "HttpError"
    this.status = status
    this.payload = payload
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  return (await response.json()) as T
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body = null, headers, method = "GET", signal } = options

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    method,
    body,
    signal,
    headers: {
      Accept: "application/json",
      ...headers,
    },
  })

  if (!response.ok) {
    let payload: ApiErrorResponse | undefined

    try {
      payload = await parseJson<ApiErrorResponse>(response)
    } catch {
      payload = undefined
    }

    throw new HttpError(
      payload?.detail || payload?.message || "Não foi possível concluir a requisição.",
      response.status,
      payload,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return parseJson<T>(response)
}

export const http = {
  delete: <T>(path: string, options?: Omit<RequestOptions, "method">) =>
    request<T>(path, { ...options, method: "DELETE" }),
  get: <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "GET" }),
  patch: <T>(path: string, body?: BodyInit | null, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, body, method: "PATCH" }),
  post: <T>(path: string, body?: BodyInit | null, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, body, method: "POST" }),
  put: <T>(path: string, body?: BodyInit | null, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, body, method: "PUT" }),
}
