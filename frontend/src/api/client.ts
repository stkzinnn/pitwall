/**
 * Minimal typed fetch wrapper for the PitWall backend. Deliberately no
 * extra HTTP library: the backend is a small, same-origin-in-spirit
 * FastAPI JSON API, so a thin fetch wrapper covers everything V1 needs.
 */

const DEFAULT_API_BASE_URL = 'http://localhost:8000'

/** Base URL of the backend API, e.g. http://localhost:8000 (no trailing
 * slash). Configured via VITE_API_BASE_URL — see .env.example. */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? DEFAULT_API_BASE_URL

/** Raised for both network-level failures (status 0) and non-2xx HTTP
 * responses (real status code + optional FastAPI `detail` message). */
export class ApiError extends Error {
  readonly status: number
  readonly detail?: string

  constructor(status: number, message: string, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

interface FastApiErrorBody {
  detail?: string
}

async function handleResponse<T>(responsePromise: Promise<Response>): Promise<T> {
  let response: Response
  try {
    response = await responsePromise
  } catch {
    throw new ApiError(0, 'Não foi possível ligar ao servidor.')
  }

  if (!response.ok) {
    let detail: string | undefined
    try {
      const body = (await response.json()) as FastApiErrorBody
      detail = body.detail
    } catch {
      // Response body wasn't JSON (or was empty) — detail stays undefined,
      // callers fall back to a status-based message.
    }
    throw new ApiError(response.status, `Pedido falhou com o estado ${response.status}`, detail)
  }

  return (await response.json()) as T
}

export function apiGet<T>(path: string): Promise<T> {
  return handleResponse<T>(fetch(`${API_BASE_URL}${path}`))
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return handleResponse<T>(
    fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  )
}
