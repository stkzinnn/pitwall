/**
 * Central route table. Add new paths here (not as raw string literals in
 * components) as future screens land — e.g. Fase 6 (construtor de
 * estratégias) and Fase 7 (comparação) will likely hang off
 * `/races/:year/:round/...`.
 */
export const ROUTES = {
  raceSelection: '/',
} as const
