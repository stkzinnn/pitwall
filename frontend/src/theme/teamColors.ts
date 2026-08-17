/**
 * Team identity colors — text/hex only, no logos or imagery (protected
 * material). These are the widely-recognized livery colors for each team,
 * used as a visual identifier (avatar background, card accent) wherever a
 * driver's team is shown.
 *
 * Keyed by the exact `TeamName` string FastF1 returns, with a couple of
 * historical/alternate names mapped to the same color where teams have
 * been renamed (e.g. AlphaTauri -> RB, Alfa Romeo -> Kick Sauber) so older
 * seasons still resolve correctly.
 */
const TEAM_COLORS: Record<string, string> = {
  'Red Bull Racing': '#3671C6',
  Ferrari: '#E8002D',
  Mercedes: '#27F4D2',
  McLaren: '#FF8000',
  'Aston Martin': '#229971',
  Alpine: '#2293D1',
  Williams: '#64C4FF',
  AlphaTauri: '#5E8FAA',
  RB: '#6692FF',
  'Alfa Romeo': '#C92D4B',
  'Kick Sauber': '#52E252',
  Sauber: '#52E252',
  'Haas F1 Team': '#B6BABD',
  Haas: '#B6BABD',
}

/** Neutral fallback for a team we don't have a color for (new/renamed
 * team, or missing data) — never leave a driver with no visual identity. */
export const FALLBACK_TEAM_COLOR = '#64748B'

export function getTeamColor(teamName: string | null): string {
  if (!teamName) return FALLBACK_TEAM_COLOR
  return TEAM_COLORS[teamName] ?? FALLBACK_TEAM_COLOR
}

export { readableTextColor } from './color'
