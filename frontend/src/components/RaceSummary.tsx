import { Link } from 'react-router-dom'
import type { DriverInfo, SessionData } from '../api/types'
import { getCountryFlag } from '../lib/countryFlag'
import { raceResultsPath } from '../routes/paths'

interface RaceSummaryProps {
  session: SessionData
  drivers: DriverInfo[]
}

const SESSION_TYPE_LABELS: Record<string, string> = {
  R: 'Corrida',
  Q: 'Qualificação',
  FP1: 'Treino Livre 1',
  FP2: 'Treino Livre 2',
  FP3: 'Treino Livre 3',
  S: 'Sprint',
}

export function RaceSummary({ session, drivers }: RaceSummaryProps) {
  const sessionLabel = SESSION_TYPE_LABELS[session.session_type] ?? session.session_type
  const flag = getCountryFlag(session.country)

  return (
    <div className="flex flex-col gap-8 rounded-xl border border-border bg-surface p-6 sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <p className="font-mono text-sm tracking-widest text-text-dim uppercase">
            {session.year} · Ronda {session.round} · {sessionLabel}
          </p>
          <h2 className="mt-1 flex items-center gap-2 text-2xl font-semibold text-text">
            {flag && <span aria-hidden="true">{flag}</span>}
            {session.event_name ?? 'Nome do evento indisponível'}
          </h2>
          {session.country && <p className="mt-1 text-sm text-text-muted">{session.country}</p>}
        </div>

        <span
          className={
            session.data_complete
              ? 'shrink-0 rounded-full border border-success/40 bg-success/10 px-3 py-1 text-xs font-medium text-success'
              : 'shrink-0 rounded-full border border-warning/40 bg-warning/10 px-3 py-1 text-xs font-medium text-warning'
          }
        >
          {session.data_complete ? 'Dados completos' : 'Dados parciais'}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-4 border-y border-border py-5 sm:grid-cols-4">
        <StatItem label="Voltas" value={session.total_laps ?? '—'} />
        <StatItem label="Pilotos" value={drivers.length} />
        <StatItem label="Paragens registadas" value={session.pit_stops.length} />
        <StatItem label="Stints" value={session.stints.length} />
      </dl>

      <Link
        to={raceResultsPath(session.year, session.round)}
        className="flex items-center justify-between gap-4 rounded-lg border border-accent/40 bg-accent/10 px-5 py-4 transition-colors hover:border-accent hover:bg-accent/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <div>
          <p className="font-medium text-text">Ver classificação da corrida</p>
          <p className="mt-0.5 text-sm text-text-muted">
            Resultado real, tempos, paragens e estratégia de cada piloto — ponto de partida para
            simular alternativas.
          </p>
        </div>
        <span className="shrink-0 font-mono text-xl text-accent" aria-hidden="true">
          →
        </span>
      </Link>
    </div>
  )
}

function StatItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs tracking-wide text-text-dim uppercase">{label}</dt>
      <dd className="mt-1 font-mono text-2xl font-semibold text-text">{value}</dd>
    </div>
  )
}
