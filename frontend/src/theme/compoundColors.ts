/**
 * Tyre compound identity — colors from the theme tokens (index.css
 * `@theme`), never hardcoded hex here. This is the single place that maps
 * a compound name to its color/short label, so every screen that shows
 * compounds (this one, and future strategy/comparison screens) stays
 * consistent.
 */

/** The three compounds the strategy builder offers — SOFT/MEDIUM/HARD
 * only, per the current scope (intermediate/wet tokens already exist in
 * the theme for when race-condition strategies are in scope). */
export const STRATEGY_COMPOUNDS = ['SOFT', 'MEDIUM', 'HARD'] as const
export type StrategyCompound = (typeof STRATEGY_COMPOUNDS)[number]

const COMPOUND_COLOR_VARS: Record<string, string> = {
  SOFT: 'var(--color-tyre-soft)',
  MEDIUM: 'var(--color-tyre-medium)',
  HARD: 'var(--color-tyre-hard)',
  INTERMEDIATE: 'var(--color-tyre-intermediate)',
  WET: 'var(--color-tyre-wet)',
}

const COMPOUND_LABELS: Record<string, string> = {
  SOFT: 'S',
  MEDIUM: 'M',
  HARD: 'H',
  INTERMEDIATE: 'I',
  WET: 'W',
}

const FALLBACK_COMPOUND_COLOR_VAR = 'var(--color-text-dim)'

export function getCompoundColorVar(compound: string): string {
  return COMPOUND_COLOR_VARS[compound] ?? FALLBACK_COMPOUND_COLOR_VAR
}

// Text color legible on each compound's badge fill. Hardcoded per compound
// (rather than computed from the hex, like theme/color.ts does for team
// colors) since the compound palette is small and fixed — SOFT/INTERMEDIATE/
// WET are dark/saturated enough for light text, MEDIUM/HARD are light
// enough to need dark text.
const COMPOUND_TEXT_COLORS: Record<string, string> = {
  SOFT: '#f5f7fa',
  MEDIUM: '#0a0d12',
  HARD: '#0a0d12',
  INTERMEDIATE: '#f5f7fa',
  WET: '#f5f7fa',
}
const FALLBACK_COMPOUND_TEXT_COLOR = '#f5f7fa'

export function getCompoundTextColor(compound: string): string {
  return COMPOUND_TEXT_COLORS[compound] ?? FALLBACK_COMPOUND_TEXT_COLOR
}

/** Single-letter badge label (S/M/H/I/W) — color alone shouldn't be the
 * only way a compound is identified (accessibility), so every tyre badge
 * shows this too. */
export function getCompoundLabel(compound: string): string {
  return COMPOUND_LABELS[compound] ?? compound.slice(0, 1).toUpperCase()
}
