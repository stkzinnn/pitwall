import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getDrivers, getRaceSession } from '../api/races'
import type { SessionData } from '../api/types'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { RaceSummary } from '../components/RaceSummary'

type Status = 'idle' | 'loading' | 'error' | 'success'

const CURRENT_YEAR = new Date().getFullYear()
const EARLIEST_SUPPORTED_YEAR = 2018 // FastF1's official timing data starts here — see docs/architecture.md.

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

export function RaceSelectionPage() {
  const [year, setYear] = useState(2023)
  const [round, setRound] = useState(1)
  const [status, setStatus] = useState<Status>('idle')
  const [session, setSession] = useState<SessionData | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus('loading')
    setErrorMessage('')

    try {
      const data = await getRaceSession(year, round)
      setSession(data)
      setStatus('success')
    } catch (error) {
      setSession(null)
      setErrorMessage(describeError(error, year, round))
      setStatus('error')
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-text">Selecionar corrida</h1>
        <p className="mt-2 max-w-xl text-text-muted">
          Escolhe o ano e a ronda para carregar os dados reais dessa sessão — voltas, pneus,
          paragens e a grelha de pilotos.
        </p>
      </div>

      <RaceSearchForm
        year={year}
        round={round}
        onYearChange={setYear}
        onRoundChange={setRound}
        onSubmit={(event) => void handleSubmit(event)}
        isLoading={status === 'loading'}
      />

      {status === 'loading' && (
        <LoadingState
          message="A carregar dados da sessão…"
          hint="Se for a primeira vez que esta corrida é pedida, o backend tem de os ir buscar ao FastF1 — pode demorar um pouco mais do que o costume."
        />
      )}

      {status === 'error' && <ErrorState message={errorMessage} />}

      {status === 'success' && session && (
        <RaceSummary session={session} drivers={getDrivers(session)} />
      )}

      {status === 'idle' && <IdleFeatureHighlights />}
    </div>
  )
}

interface RaceSearchFormProps {
  year: number
  round: number
  onYearChange: (year: number) => void
  onRoundChange: (round: number) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  isLoading: boolean
}

function RaceSearchForm({
  year,
  round,
  onYearChange,
  onRoundChange,
  onSubmit,
  isLoading,
}: RaceSearchFormProps) {
  return (
    <form
      onSubmit={onSubmit}
      className="rounded-xl border border-border bg-surface p-6 shadow-[0_1px_0_0_rgba(255,255,255,0.03)_inset]"
    >
      <div className="flex flex-wrap items-end gap-5">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="year" className="text-sm font-medium text-text-muted">
            Ano
          </label>
          <input
            id="year"
            type="number"
            inputMode="numeric"
            min={EARLIEST_SUPPORTED_YEAR}
            max={CURRENT_YEAR}
            value={year}
            onChange={(event) => onYearChange(Number(event.target.value))}
            className="w-28 rounded-md border border-border-strong bg-surface-raised px-3 py-2.5 font-mono text-lg text-text focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="round" className="text-sm font-medium text-text-muted">
            Ronda
          </label>
          <input
            id="round"
            type="number"
            inputMode="numeric"
            min={1}
            max={30}
            value={round}
            onChange={(event) => onRoundChange(Number(event.target.value))}
            className="w-24 rounded-md border border-border-strong bg-surface-raised px-3 py-2.5 font-mono text-lg text-text focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="rounded-md bg-accent px-6 py-2.5 font-medium text-bg transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? 'A carregar…' : 'Carregar corrida'}
        </button>
      </div>

      <p className="mt-4 text-xs text-text-dim">
        Cobertura completa a partir de {EARLIEST_SUPPORTED_YEAR} (timing oficial da F1 via
        FastF1).
      </p>
    </form>
  )
}

const FEATURES: { accentVar: string; title: string; description: string }[] = [
  {
    accentVar: 'var(--color-tyre-soft)',
    title: 'Dados reais',
    description:
      'Ingeridos diretamente do FastF1 — voltas, pit stops, composto de pneu e períodos de Safety Car/VSC.',
  },
  {
    accentVar: 'var(--color-tyre-medium)',
    title: 'Estratégias alternativas',
    description:
      'Simula cenários hipotéticos de pneus/paragens e compara-os com o que aconteceu de facto (próxima etapa).',
  },
  {
    accentVar: 'var(--color-accent)',
    title: 'Comparação lado a lado',
    description: 'Estratégias ordenadas por tempo estimado, com a diferença face à melhor.',
  },
]

function IdleFeatureHighlights() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {FEATURES.map((feature) => (
        <div
          key={feature.title}
          className="rounded-lg border border-border bg-surface p-5"
          style={{ borderTopColor: feature.accentVar, borderTopWidth: 2 }}
        >
          <h3 className="font-medium text-text">{feature.title}</h3>
          <p className="mt-1.5 text-sm text-text-muted">{feature.description}</p>
        </div>
      ))}
    </div>
  )
}
