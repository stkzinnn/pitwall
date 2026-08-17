import type { SessionData } from '../api/types'
import { getOrderedResults } from './raceResults'

/**
 * Estimates a driver's grid position under a SIMULATED strategy, keeping
 * every other driver frozen at their real result.
 *
 * ASSUMPTION (shown to the user, not hidden): this answers "what if only
 * this driver had run this alternative strategy, and everyone else had
 * driven exactly as they really did?" — it does NOT simulate how other
 * drivers would have reacted (undercut/overcut, traffic, etc.).
 *
 * TIME-BASE CONSISTENCY: POST /api/v1/compare returns
 * `estimated_total_time_seconds` calibrated against `real_total_time_seconds`
 * — literally the sum of this driver's own recorded lap times (see
 * backend/app/simulation/engine.py `_sum_real_lap_times`). To slot that
 * estimate into the real grid fairly, every OTHER driver's "real total"
 * used for comparison here is computed the exact same way (sum of their
 * own lap_time_seconds, from the already-loaded SessionData.laps) —
 * NOT the official FIA classification time/gap (session.results), which
 * is a related but distinct figure.
 *
 * In practice these two bases coincide almost exactly for any driver who
 * completed the full race distance — verified against 2023 Bahrain: the
 * sum-of-laps gap and the official gap matched to ~1e-13s for every
 * lead-lap finisher. They do NOT reliably coincide for lapped/retired
 * drivers (spot-checked the same race: one lapped driver's sum-of-laps
 * gap was off by ~15s from the official one, most likely a data quirk on
 * that specific lap). So: a driver is only included in the reordering if
 * they completed the same number of laps as the race distance
 * (`session.total_laps`) — anyone lapped or retired (real or, if it's the
 * selected driver, hypothetically) is left out of the comparison and
 * keeps their real position, rather than guessing at a basis we've shown
 * isn't reliable for them.
 */

export interface PositionEstimate {
  isComparable: boolean
  /** Set when isComparable is false, for a clear message instead of just
   * hiding the feature. */
  reason: string | null
  realPosition: number | null
  estimatedPosition: number | null
}

function validLapCount(session: SessionData, driverCode: string): number {
  return session.laps.filter((lap) => lap.driver === driverCode && lap.lap_time_seconds !== null)
    .length
}

function realTotalSeconds(session: SessionData, driverCode: string): number {
  return session.laps
    .filter((lap) => lap.driver === driverCode && lap.lap_time_seconds !== null)
    .reduce((sum, lap) => sum + (lap.lap_time_seconds ?? 0), 0)
}

/** The race distance to require for a driver to be "comparable" — from
 * SessionData.total_laps, falling back to the longest lap count actually
 * recorded by any driver if that's ever missing. */
function referenceLapCount(session: SessionData): number | null {
  if (session.total_laps !== null) return session.total_laps
  const counts = session.drivers.map((driver) => validLapCount(session, driver.code))
  return counts.length > 0 ? Math.max(...counts) : null
}

export function estimatePosition(
  session: SessionData,
  driverCode: string,
  estimatedTotalTimeSeconds: number | null,
): PositionEstimate {
  const realResult = session.results.find((result) => result.code === driverCode) ?? null
  const realPosition = realResult?.position ?? null

  if (estimatedTotalTimeSeconds === null) {
    return { isComparable: false, reason: 'Sem tempo estimado para esta estratégia.', realPosition, estimatedPosition: null }
  }

  const laps = referenceLapCount(session)
  if (laps === null) {
    return {
      isComparable: false,
      reason: 'Sem voltas totais da corrida para comparar posições.',
      realPosition,
      estimatedPosition: null,
    }
  }

  if (validLapCount(session, driverCode) < laps) {
    return {
      isComparable: false,
      reason:
        'Este piloto não completou a corrida toda na realidade (voltas em atraso ou abandono) — a comparação de posição não é fiável.',
      realPosition,
      estimatedPosition: null,
    }
  }

  const comparable: { code: string; totalSeconds: number }[] = []
  const behind: string[] = []

  for (const result of getOrderedResults(session)) {
    if (result.code === driverCode) {
      comparable.push({ code: driverCode, totalSeconds: estimatedTotalTimeSeconds })
      continue
    }
    if (validLapCount(session, result.code) < laps) {
      behind.push(result.code)
      continue
    }
    comparable.push({ code: result.code, totalSeconds: realTotalSeconds(session, result.code) })
  }

  comparable.sort((a, b) => a.totalSeconds - b.totalSeconds)
  const fullOrder = [...comparable.map((entry) => entry.code), ...behind]

  return {
    isComparable: true,
    reason: null,
    realPosition,
    estimatedPosition: fullOrder.indexOf(driverCode) + 1,
  }
}
