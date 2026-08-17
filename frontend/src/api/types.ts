/**
 * Typed mirrors of the backend's Pydantic schemas
 * (backend/app/schemas/session.py). Field names match the JSON wire
 * format exactly (snake_case) — no client-side renaming, so a diff
 * against the backend schema is a straight visual comparison.
 */

export interface Lap {
  driver: string
  lap_number: number
  lap_time_seconds: number | null
  sector_1_seconds: number | null
  sector_2_seconds: number | null
  sector_3_seconds: number | null
  compound: string | null
  tyre_life: number | null
  position: number | null
  track_status: string | null
}

export interface PitStop {
  driver: string
  lap_number: number
  duration_seconds: number | null
}

export interface Stint {
  driver: string
  stint_number: number
  compound: string | null
  start_lap: number
  end_lap: number
}

/** Static per-driver info (not per-lap) — name/number/team. Fields beyond
 * `code` may be null when the backend couldn't derive them (older/partial
 * sessions) — always render a fallback, never assume they're present. */
export interface DriverInfo {
  code: string
  full_name: string | null
  number: number | null
  team_name: string | null
}

export interface SessionData {
  year: number
  round: number
  session_type: string
  event_name: string | null
  country: string | null
  total_laps: number | null
  laps: Lap[]
  pit_stops: PitStop[]
  stints: Stint[]
  drivers: DriverInfo[]
  data_complete: boolean
}
