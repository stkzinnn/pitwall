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

/**
 * Final classification for one driver. Pit-stop count and real tyre
 * strategy aren't duplicated here — derive them from SessionData.pit_stops
 * / SessionData.stints, filtered by `code` (see lib/raceResults.ts).
 */
export interface DriverResult {
  code: string
  position: number | null
  classified_position: string | null
  status: string | null
  /** Set only for the race winner. */
  total_time_seconds: number | null
  /** Set for everyone except the winner. */
  gap_to_leader_seconds: number | null
  points: number | null
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
  results: DriverResult[]
  data_complete: boolean
}

/**
 * Mirrors backend/app/schemas/simulation.py exactly (field names, shape).
 * Built by the strategy builder screen; sent as-is (no reshaping) to
 * POST /api/v1/compare — see StrategyBuilderPage.
 */
export interface StintPlan {
  compound: string
  number_of_laps: number
}

export interface NamedStrategy {
  label: string
  strategy: StintPlan[]
}

export interface ComparisonRequestBody {
  driver: string
  year: number
  round: number
  session_type: string
  strategies: NamedStrategy[]
}

export interface SafetyCarPeriod {
  laps: number[]
  time_lost_seconds: number
}

export interface SimulationResult {
  driver: string
  estimated_total_time_seconds: number | null
  real_total_time_seconds: number | null
  difference_seconds: number | null
  safety_car_time_added_seconds: number
  safety_car_periods: SafetyCarPeriod[]
  warnings: string[]
}

export interface StrategyComparisonEntry {
  label: string
  result: SimulationResult
  delta_to_best_seconds: number | null
  has_warnings: boolean
}

export interface ComparisonResult {
  driver: string
  year: number
  round: number
  session_type: string
  best_label: string | null
  best_estimated_total_time_seconds: number | null
  strategies: StrategyComparisonEntry[]
}
