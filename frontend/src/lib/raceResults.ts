import type { DriverResult, SessionData, Stint, StintPlan } from '../api/types'

/** Final classification, ordered by position — drivers without a
 * position (shouldn't normally happen, but data can be partial) sort
 * last rather than breaking the ordering. */
export function getOrderedResults(session: SessionData): DriverResult[] {
  return [...session.results].sort((a, b) => {
    if (a.position === null && b.position === null) return 0
    if (a.position === null) return 1
    if (b.position === null) return -1
    return a.position - b.position
  })
}

export function getPitStopCount(session: SessionData, driverCode: string): number {
  return session.pit_stops.filter((stop) => stop.driver === driverCode).length
}

export function getDriverStints(session: SessionData, driverCode: string): Stint[] {
  return session.stints
    .filter((stint) => stint.driver === driverCode)
    .sort((a, b) => a.stint_number - b.stint_number)
}

/** Adapts real Stints (start_lap/end_lap) into the StintPlan shape
 * (number_of_laps) the StrategyBar component already renders — same bar,
 * same visual language, whether it's showing a real or a planned
 * strategy. */
export function stintsToStintPlans(stints: Stint[]): StintPlan[] {
  return stints.map((stint) => ({
    compound: stint.compound ?? 'UNKNOWN',
    number_of_laps: stint.end_lap - stint.start_lap + 1,
  }))
}
