import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { DriverInfo } from '../api/types'
import { getTeamColor } from '../theme/teamColors'
import { DriverAvatar } from './DriverAvatar'

interface DriverCardProps {
  driver: DriverInfo
  /** When given, the card navigates there on click/Enter (e.g. the
   * strategy builder for this driver) and is keyboard-focusable. Omit for
   * a purely informational card (e.g. the driver highlight in the
   * strategy screen's own header) — same visual language, no navigation. */
  to?: string
}

const CARD_CLASSES =
  'group flex items-center gap-3 rounded-lg border border-border bg-surface-raised p-3 transition-all duration-150'
const INTERACTIVE_CLASSES =
  'hover:-translate-y-0.5 hover:border-border-strong hover:shadow-[0_8px_20px_-8px_rgba(0,0,0,0.6)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent'

/** A driver's card: avatar, name, team, number — with a team-colored left
 * accent for instant visual identification. */
export function DriverCard({ driver, to }: DriverCardProps) {
  const accentColor = getTeamColor(driver.team_name)
  const style = { borderLeftColor: accentColor, borderLeftWidth: 3 }
  const content = <DriverCardContent driver={driver} accentColor={accentColor} />

  if (to) {
    return (
      <Link to={to} className={`${CARD_CLASSES} ${INTERACTIVE_CLASSES}`} style={style}>
        {content}
      </Link>
    )
  }

  return (
    <div className={CARD_CLASSES} style={style}>
      {content}
    </div>
  )
}

function DriverCardContent({
  driver,
  accentColor,
}: {
  driver: DriverInfo
  accentColor: string
}): ReactNode {
  return (
    <>
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
    </>
  )
}
