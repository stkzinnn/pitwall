/**
 * Central route table. Add new paths here (not as raw string literals in
 * components) as future screens land — e.g. Fase 7 (comparação de
 * estratégias) will likely reuse the same /races/:year/:round/... prefix.
 */
export const ROUTES = {
  raceSelection: '/',
  raceResults: '/races/:year/:round/results',
  strategyBuilder: '/races/:year/:round/drivers/:driver/strategy',
} as const

/** Builds a concrete results-screen URL for a given race. */
export function raceResultsPath(year: number, round: number): string {
  return `/races/${year}/${round}/results`
}

/** Builds a concrete strategy-builder URL for a given race/driver — use
 * this instead of string-templating ROUTES.strategyBuilder by hand. */
export function strategyBuilderPath(year: number, round: number, driver: string): string {
  return `/races/${year}/${round}/drivers/${driver}/strategy`
}
