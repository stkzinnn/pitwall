import type { DriverInfo } from '../api/types'
import { getInitials } from '../lib/driverDisplay'
import { getTeamColor, readableTextColor } from '../theme/teamColors'

interface DriverAvatarProps {
  driver: DriverInfo
  size?: number
}

/** Circular avatar with the driver's initials over their team color — no
 * external images (headshots are protected material), just a color +
 * text identity. */
export function DriverAvatar({ driver, size = 44 }: DriverAvatarProps) {
  const backgroundColor = getTeamColor(driver.team_name)
  const color = readableTextColor(backgroundColor)

  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-full font-mono font-semibold"
      style={{ width: size, height: size, backgroundColor, color, fontSize: size * 0.36 }}
      aria-hidden="true"
    >
      {getInitials(driver)}
    </span>
  )
}
