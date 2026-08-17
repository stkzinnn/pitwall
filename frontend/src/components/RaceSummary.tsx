import type { DriverInfo, SessionData } from '../api/types'
import { getCountryFlag } from '../lib/countryFlag'
import { groupByTeam } from '../lib/driverDisplay'
import { DriverCard } from './DriverCard'

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
  // Team pairs end up adjacent in the grid without needing group headers —
  // each card already shows its own team name.
  const orderedDrivers = groupByTeam(drivers).flatMap((group) => group.drivers)

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

      <div>
        <h3 className="mb-3 text-sm font-medium text-text-muted">Pilotos</h3>
        {orderedDrivers.length > 0 ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {orderedDrivers.map((driver) => (
              <DriverCard key={driver.code} driver={driver} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-dim">Sem dados de pilotos para esta sessão.</p>
        )}
      </div>
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
