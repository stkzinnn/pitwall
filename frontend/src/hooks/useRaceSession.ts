import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getRaceSession } from '../api/races'
import type { SessionData } from '../api/types'

type Status = 'loading' | 'error' | 'success'

interface UseRaceSessionResult {
  status: Status
  session: SessionData | null
  errorMessage: string
}

function describeError(error: unknown, year: number, round: number): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return `Não encontrámos a ronda ${round} de ${year}. Confirma o ano e o número da ronda.`
    }
    if (error.status === 0) {
      return (
        'Não foi possível ligar ao backend. Confirma que está a correr em ' +
        'localhost:8000 (ou o endereço configurado em VITE_API_BASE_URL).'
      )
    }
    return 'O backend devolveu um erro inesperado. Tenta novamente daqui a pouco.'
  }
  return 'Ocorreu um erro inesperado ao carregar a corrida.'
}

/** Fetches a race session on mount (and whenever year/round change) —
 * shared by every screen that's reached directly via a /races/:year/:round
 * URL (results, strategy builder) rather than via the selection form. */
export function useRaceSession(year: number, round: number): UseRaceSessionResult {
  const [status, setStatus] = useState<Status>('loading')
  const [session, setSession] = useState<SessionData | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    let cancelled = false

    if (!Number.isFinite(year) || !Number.isFinite(round)) {
      setErrorMessage('Corrida inválida na ligação.')
      setStatus('error')
      return
    }

    setStatus('loading')
    getRaceSession(year, round)
      .then((data) => {
        if (cancelled) return
        setSession(data)
        setStatus('success')
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setErrorMessage(describeError(error, year, round))
        setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [year, round])

  return { status, session, errorMessage }
}
