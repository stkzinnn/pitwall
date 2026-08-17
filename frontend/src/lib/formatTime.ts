/** Formats an absolute duration (the race winner's total time) as
 * H:MM:SS.mmm, matching how official F1 timing shows a race winner's
 * time. */
export function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  const minutesStr = hours > 0 ? String(minutes).padStart(2, '0') : String(minutes)
  const secondsStr = seconds.toFixed(3).padStart(6, '0')

  return hours > 0 ? `${hours}:${minutesStr}:${secondsStr}` : `${minutesStr}:${secondsStr}`
}

/** What to show in a results row's time/gap column: the winner's total
 * time, everyone else's gap, or their finishing status (e.g. "Retired")
 * when neither time nor gap is available. */
export function formatRaceTimeOrStatus(result: {
  total_time_seconds: number | null
  gap_to_leader_seconds: number | null
  status: string | null
}): string {
  if (result.total_time_seconds !== null) {
    return formatDuration(result.total_time_seconds)
  }
  if (result.gap_to_leader_seconds !== null) {
    return `+${result.gap_to_leader_seconds.toFixed(3)}s`
  }
  return result.status ?? '—'
}
