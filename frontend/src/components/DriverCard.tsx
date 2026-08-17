import type { DriverInfo } from '../api/types'
import { getTeamColor } from '../theme/teamColors'
import { DriverAvatar } from './DriverAvatar'

interface DriverCardProps {
  driver: DriverInfo
}

/** A driver's card: avatar, name, team, number — with a team-colored left
 * accent for instant visual identification. Styled to read as clickable
 * (hover lift, focus ring) ahead of the strategy screen it'll navigate to
 * in the next phase; no onClick yet, that's wired up when that screen
 * exists. */
export function DriverCard({ driver }: DriverCardProps) {
  const accentColor = getTeamColor(driver.team_name)

  return (
    <div
      className="group flex items-center gap-3 rounded-lg border border-border bg-surface-raised p-3 transition-all duration-150 hover:-translate-y-0.5 hover:border-border-strong hover:shadow-[0_8px_20px_-8px_rgba(0,0,0,0.6)]"
      style={{ borderLeftColor: accentColor, borderLeftWidth: 3 }}
    >
      <DriverAvatar driver={driver} />

      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-text">{driver.full_name ?? driver.code}</p>
        <p className="truncate text-xs text-text-muted">
          {driver.team_name ?? 'Equipa desconhecida'}
        </p>
      </div>

      <div className="flex flex-col items-end gap-0.5">
        <span className="font-mono text-xs tracking-wider text-text-dim">{driver.code}</span>
        {driver.number !== null && (
          <span className="font-mono text-lg leading-none font-bold" style={{ color: accentColor }}>
            {driver.number}
          </span>
        )}
      </div>
    </div>
  )
}
