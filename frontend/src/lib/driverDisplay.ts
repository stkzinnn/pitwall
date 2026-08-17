import type { DriverInfo } from '../api/types'

/** Avatar initials: from the full name when we have one ("Max
 * Verstappen" -> "MV"), otherwise the first two letters of the driver
 * code ("VER" -> "VE") — never blank. */
export function getInitials(driver: DriverInfo): string {
  if (driver.full_name) {
    const parts = driver.full_name.trim().split(/\s+/)
    const first = parts[0]?.[0] ?? ''
    const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : ''
    const initials = (first + last).toUpperCase()
    if (initials) return initials
  }
  return driver.code.slice(0, 2).toUpperCase()
}

/** Groups drivers by team (unnamed/unknown team drivers fall into their
 * own "no team" bucket, keyed by empty string), preserving each team's
 * first-appearance order and, within a team, the drivers' original order
 * — so the two drivers of a team end up adjacent for the card grid. */
export function groupByTeam(drivers: DriverInfo[]): { team: string | null; drivers: DriverInfo[] }[] {
  const order: (string | null)[] = []
  const groups = new Map<string | null, DriverInfo[]>()

  for (const driver of drivers) {
    const key = driver.team_name
    if (!groups.has(key)) {
      groups.set(key, [])
      order.push(key)
    }
    groups.get(key)?.push(driver)
  }

  return order.map((team) => ({ team, drivers: groups.get(team) ?? [] }))
}
