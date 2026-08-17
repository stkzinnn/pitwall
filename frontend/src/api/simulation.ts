import { apiPost } from './client'
import type { ComparisonRequestBody, ComparisonResult, NamedStrategy } from './types'

/** POST /api/v1/compare — runs every named strategy through the backend's
 * simulation engine for one driver and returns them ordered by estimated
 * time. Doesn't reshape `strategies`: it's already exactly the
 * NamedStrategy[] the backend expects. */
export function compareStrategies(
  driver: string,
  year: number,
  round: number,
  strategies: NamedStrategy[],
): Promise<ComparisonResult> {
  const body: ComparisonRequestBody = {
    driver,
    year,
    round,
    session_type: 'R',
    strategies,
  }
  return apiPost<ComparisonResult>('/api/v1/compare', body)
}
