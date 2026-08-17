import type { KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDrivers } from '../api/races'
import type { DriverResult, SessionData } from '../api/types'
import { formatRaceTimeOrStatus } from '../lib/formatTime'
import { getDriverStints, getPitStopCount, stintsToStintPlans } from '../lib/raceResults'
import { strategyBuilderPath } from '../routes/paths'
import { DriverAvatar } from './DriverAvatar'
import { StrategyBar } from './StrategyBar'

interface ResultsRowProps {
  session: SessionData
  result: DriverResult
}

/** One row of the classification table — the whole row navigates to that
 * driver's strategy builder (click, or Enter/Space while focused). Using
 * role="link" on a <tr> is an imperfect ARIA fit (a table row isn't
 * really a link), but it's the pragmatic choice here: it keeps real
 * <table>/<td> semantics for the tabular data itself while still
 * announcing "this whole row is one interactive target" to assistive
 * tech, which matches how it actually behaves. */
export function ResultsRow({ session, result }: ResultsRowProps) {
  const navigate = useNavigate()
  const driver = getDrivers(session).find((candidate) => candidate.code === result.code) ?? {
    code: result.code,
    full_name: null,
    number: null,
    team_name: null,
  }
  const stints = getDriverStints(session, result.code)
  const pitStopCount = getPitStopCount(session, result.code)
  const target = strategyBuilderPath(session.year, session.round, result.code)

  function goToStrategy() {
    navigate(target)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTableRowElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      goToStrategy()
    }
  }

  return (
    <tr
      onClick={goToStrategy}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="link"
      aria-label={`Montar estratégia para ${driver.full_name ?? driver.code}`}
      className="cursor-pointer border-b border-border transition-colors last:border-b-0 hover:bg-surface-raised focus-visible:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset"
    >
      <td className="px-4 py-3 whitespace-nowrap">
        {result.position !== null ? (
          <span
            className={
              result.position <= 3
                ? 'font-mono text-lg font-bold text-accent'
                : 'font-mono text-lg font-bold text-text'
            }
          >
            P{result.position}
          </span>
        ) : (
          <span className="font-mono text-text-dim">—</span>
        )}
      </td>

      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <DriverAvatar driver={driver} size={36} />
          <div className="min-w-0">
            <p className="truncate font-medium text-text">{driver.full_name ?? driver.code}</p>
            <p className="truncate text-xs text-text-muted">
              {driver.team_name ?? 'Equipa desconhecida'}
            </p>
          </div>
        </div>
      </td>

      <td className="px-4 py-3 text-right font-mono text-sm whitespace-nowrap text-text">
        {formatRaceTimeOrStatus(result)}
      </td>

      <td className="px-4 py-3 text-center font-mono text-sm text-text-muted">{pitStopCount}</td>

      <td className="px-4 py-3">
        <div className="w-40 sm:w-52">
          <StrategyBar strategy={stintsToStintPlans(stints)} raceTotalLaps={session.total_laps} />
        </div>
      </td>
    </tr>
  )
}
