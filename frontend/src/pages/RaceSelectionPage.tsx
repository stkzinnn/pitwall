import { lazy, Suspense, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getDrivers, getRaceSession } from '../api/races'
import type { SessionData } from '../api/types'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { RaceSummary } from '../components/RaceSummary'

// three.js (~600kB) is only ever needed for this one hero background —
// lazy-loaded so every other route's bundle stays free of it, and so it
// doesn't block this page's own first paint (the hero copy/form render
// immediately; the 3D scene fades in once its chunk arrives).
const RaceBackground = lazy(() =>
  import('../components/RaceBackground').then((module) => ({ default: module.RaceBackground })),
)

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
      <section className="relative isolate left-1/2 right-1/2 -mx-[50vw] flex min-h-[calc(100vh-4.5rem)] w-screen items-center overflow-hidden bg-bg">
        {/* 3D circuit — confined to the right portion of the hero only, so
            it never sits under the title/form (see RaceBackground.tsx). */}
        <div className="absolute inset-y-0 right-0 hidden w-full sm:block sm:w-[62%] lg:w-[58%]">
          <Suspense fallback={null}>
            <RaceBackground className="absolute inset-0 h-full w-full" />
          </Suspense>
        </div>

        {/* Cinematic layers — CSS only, all pointer-events:none, sit above
            the canvas but below the text/form. */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 85% 75% at 72% 42%, transparent 25%, var(--color-bg) 100%)',
          }}
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage:
              'repeating-linear-gradient(to bottom, var(--color-text) 0px, var(--color-text) 1px, transparent 1px, transparent 3px)',
          }}
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-bg to-transparent"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-bg to-transparent"
          aria-hidden="true"
        />

        <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-col items-start gap-12 px-6 py-20 lg:flex-row lg:items-center lg:justify-between lg:gap-10 lg:px-10">
          <div className="flex max-w-xl flex-col gap-7">
            <LiveDataBadge />
            <HeroHeadline />
            <p className="max-w-md text-base text-text-muted sm:text-lg">
              Escolhe o ano e a ronda para carregar os dados reais dessa sessão — voltas, pneus,
              paragens e a grelha de pilotos.
            </p>

            <RaceSearchForm
              year={year}
              round={round}
              onYearChange={setYear}
              onRoundChange={setRound}
              onSubmit={(event) => void handleSubmit(event)}
              isLoading={status === 'loading'}
            />
          </div>

          <TelemetryDemoPanel />
        </div>

        <ScrollCue />
      </section>

      <HeroStatsStrip />

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

/** "Dados oficiais · FastF1" pill with a pulsing brand-red dot — a status
 * light, not a win/loss signal, so it uses the brand accent, never
 * --color-success (reserved for "better/faster/won" — see index.css). */
function LiveDataBadge() {
  return (
    <div className="flex items-center gap-2 text-xs tracking-[0.2em] text-text-muted uppercase">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75 motion-reduce:animate-none" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
      </span>
      <span className="font-mono">Dados oficiais · FastF1</span>
    </div>
  )
}

/** The editorial headline: mostly filled, part outlined
 * (-webkit-text-stroke), one keyword in the brand accent with a glow —
 * per the redesign brief's mixed typographic treatment. */
function HeroHeadline() {
  return (
    <h1 className="font-display text-[clamp(2.75rem,7vw,8.125rem)] leading-[0.92] font-black tracking-tight text-balance">
      <span className="block text-text">Reescreve</span>
      <span className="block">
        <span
          style={{ WebkitTextStroke: '1.5px var(--color-text)', color: 'transparent' }}
        >
          a{' '}
        </span>
        <span
          className="text-accent"
          style={{ textShadow: '0 0 28px color-mix(in srgb, var(--color-accent) 55%, transparent)' }}
        >
          corrida
        </span>
        <span
          style={{ WebkitTextStroke: '1.5px var(--color-text)', color: 'transparent' }}
        >
          .
        </span>
      </span>
    </h1>
  )
}

/**
 * A small "telemetry is running" panel, floating on the right over the 3D
 * scene — HONESTY NOTE (deliberate choice, not an oversight): every number
 * here is real, not invented. The stint sequence and the −16.3s delta are
 * the actual output of this project's own simulation engine replaying
 * GAS's real 2023 Bahrain strategy against his real race time (see
 * backend/tests/test_engine_regression.py for the same methodology, and
 * the investigation in this repo's history for this exact figure) — it's
 * a genuine "same strategy, engine's estimate vs. what really happened"
 * result, not a hypothetical faster strategy, hence the caption. The
 * sparkline is explicitly NOT a chart of this or any data — it's a
 * decorative motion cue (a "telemetry pulse") and never claims to encode
 * a real measurement.
 */
function TelemetryDemoPanel() {
  return (
    <div className="hidden w-72 shrink-0 flex-col gap-4 rounded-2xl border border-border-strong bg-surface/55 p-5 shadow-[0_24px_60px_-24px_rgba(0,0,0,0.7)] backdrop-blur-lg lg:flex">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[10px] tracking-[0.25em] text-text-dim uppercase">
          Exemplo real · Bahrain 2023
        </p>
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
      </div>

      <div className="flex flex-col gap-2">
        <TelemetryStintLine compound="SOFT" laps="Voltas 1–9" />
        <TelemetryStintLine compound="HARD" laps="Voltas 10–40" note="2 stints" />
        <TelemetryStintLine compound="SOFT" laps="Voltas 41–57" />
      </div>

      <TelemetryPulse />

      <div className="flex items-end justify-between gap-3 border-t border-border pt-3">
        <div>
          <p className="text-[10px] tracking-wide text-text-dim uppercase">Δ replay do motor</p>
          <p className="mt-0.5 text-[11px] text-text-dim">mesma estratégia real, GAS</p>
        </div>
        <p className="font-mono text-lg font-bold text-success">−16.3s</p>
      </div>
    </div>
  )
}

function TelemetryStintLine({
  compound,
  laps,
  note,
}: {
  compound: 'SOFT' | 'HARD'
  laps: string
  note?: string
}) {
  const fill = compound === 'SOFT' ? 'var(--color-tyre-soft)' : 'var(--color-tyre-hard)'
  const textColor = compound === 'SOFT' ? '#fdeff0' : '#0b0708'
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="flex h-5 w-9 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-bold"
        style={{ backgroundColor: fill, color: textColor }}
      >
        {compound === 'SOFT' ? 'S' : 'H'}
      </span>
      <span className="font-mono text-xs text-text-muted">{laps}</span>
      {note && <span className="font-mono text-[10px] text-text-dim">({note})</span>}
    </div>
  )
}

/** Purely decorative motion — an animated waveform suggesting "telemetry
 * is streaming", not a chart of any real measurement (see
 * TelemetryDemoPanel's doc comment on data honesty). */
function TelemetryPulse() {
  return (
    <svg viewBox="0 0 240 40" className="h-8 w-full overflow-visible" aria-hidden="true">
      <polyline
        className="animate-telemetry-pulse motion-reduce:animate-none"
        points="0,20 20,20 30,8 40,32 50,14 60,20 90,20 100,6 110,34 120,20 150,20 160,10 170,30 180,20 210,20 220,12 230,26 240,20"
        fill="none"
        stroke="var(--color-accent)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.7"
      />
    </svg>
  )
}

/** Real, verifiable numbers only — no invented stats (see brief). Season
 * coverage is computed from the same constants the year input already
 * validates against, so it can never drift out of sync or need manual
 * updates. */
function HeroStatsStrip() {
  const seasonsCovered = CURRENT_YEAR - EARLIEST_SUPPORTED_YEAR + 1
  const stats = [
    { value: String(seasonsCovered), label: `Temporadas cobertas (${EARLIEST_SUPPORTED_YEAR}–${CURRENT_YEAR})` },
    { value: '57', label: 'Voltas · corrida-exemplo (Bahrain 2023)' },
    { value: '±4.3s', label: 'Erro típico do modelo numa corrida validada (VER, Bahrain 2023)' },
    { value: '20', label: 'Pilotos por corrida' },
  ]

  return (
    <div className="grid grid-cols-2 gap-6 border-y border-border py-8 sm:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label}>
          <p className="font-mono text-3xl font-bold text-text sm:text-4xl">{stat.value}</p>
          <p className="mt-1 text-xs text-text-dim">{stat.label}</p>
        </div>
      ))}
    </div>
  )
}

function ScrollCue() {
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-6 z-10 flex justify-center">
      <div className="flex flex-col items-center gap-2 text-text-dim">
        <span className="font-mono text-[10px] tracking-[0.3em] uppercase">Scroll</span>
        <span className="h-8 w-5 rounded-full border border-border-strong">
          <span className="mx-auto mt-1.5 block h-1.5 w-1 animate-scroll-cue rounded-full bg-text-dim motion-reduce:animate-none" />
        </span>
      </div>
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
      className="w-fit rounded-xl border border-border-strong bg-surface/55 p-6 shadow-[0_1px_0_0_rgba(255,255,255,0.03)_inset] backdrop-blur-md"
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
          className="rounded-md bg-accent px-6 py-2.5 font-medium text-white transition-[background-color,box-shadow] duration-200 hover:bg-accent-strong hover:shadow-[0_0_24px_color-mix(in_srgb,var(--color-accent)_65%,transparent)] disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
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
          className="rounded-lg border border-border bg-surface/80 p-5 backdrop-blur-sm transition-colors hover:border-border-strong"
          style={{ borderTopColor: feature.accentVar, borderTopWidth: 2 }}
        >
          <h3 className="font-display font-bold text-text">{feature.title}</h3>
          <p className="mt-1.5 text-sm text-text-muted">{feature.description}</p>
        </div>
      ))}
    </div>
  )
}
