import { apiGet } from './client'
import type { DriverInfo, SessionData } from './types'

/** GET /api/v1/races/{year}/{round} — normalized laps/pit stops/stints
 * for one session, ingested from FastF1 (or read back from the backend's
 * cache — see backend/app/api/v1/races.py). */
export function getRaceSession(
  year: number,
  round: number,
  sessionType: string = 'R',
): Promise<SessionData> {
  const params = new URLSearchParams({ session_type: sessionType })
  return apiGet<SessionData>(`/api/v1/races/${year}/${round}?${params.toString()}`)
}

/** The session's drivers, in the order the backend derived them (roughly
 * grid order). Falls back to deriving bare (code-only) entries from the
 * laps if `drivers` came back empty — e.g. a session cached by an older
 * backend version, before driver info existed. */
export function getDrivers(session: SessionData): DriverInfo[] {
  if (session.drivers.length > 0) {
    return session.drivers
  }

  const seen = new Set<string>()
  const drivers: DriverInfo[] = []
  for (const lap of session.laps) {
    if (!seen.has(lap.driver)) {
      seen.add(lap.driver)
      drivers.push({ code: lap.driver, full_name: null, number: null, team_name: null })
    }
  }
  return drivers
}
