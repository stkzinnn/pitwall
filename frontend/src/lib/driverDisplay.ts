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
