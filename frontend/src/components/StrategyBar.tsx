import type { StintPlan } from '../api/types'
import { getCompoundColorVar, getCompoundLabel } from '../theme/compoundColors'

interface StrategyBarProps {
  strategy: StintPlan[]
  /** Race distance to scale against — see module doc for why. */
  raceTotalLaps: number | null
}

/**
 * The strategy as a single horizontal bar: each stint is a segment
 * colored by compound, width proportional to its lap count — meant to
 * read "vermelho curto → branco longo" at a glance, no text required.
 *
 * Scaled against `max(strategy laps, race total laps)`, not just the
 * strategy's own total: if the planned strategy falls short of the race
 * distance, the bar visibly stops short of the container's right edge
 * (plain background showing through) instead of always stretching to
 * fill 100% — a second, implicit cue alongside the numeric comparison in
 * StrategyEditor that this strategy doesn't (yet) cover the full race.
 */
export function StrategyBar({ strategy, raceTotalLaps }: StrategyBarProps) {
  const strategyTotalLaps = strategy.reduce((sum, stint) => sum + stint.number_of_laps, 0)
  const scale = Math.max(strategyTotalLaps, raceTotalLaps ?? 0, 1)

  if (strategy.length === 0) {
    return (
      <div className="flex h-10 items-center justify-center rounded-md border border-dashed border-border text-xs text-text-dim">
        Sem stints
      </div>
    )
  }

  return (
    <div className="flex h-10 w-full overflow-hidden rounded-md bg-surface" role="img" aria-label="Sequência de stints da estratégia">
      {strategy.map((stint, index) => {
        const widthPercent = (stint.number_of_laps / scale) * 100
        return (
          <div
            key={index}
            className="flex min-w-[2px] items-center justify-center border-r border-bg/40 font-mono text-xs font-semibold last:border-r-0"
            style={{
              width: `${widthPercent}%`,
              backgroundColor: getCompoundColorVar(stint.compound),
              color: 'var(--color-bg)',
            }}
            title={`${stint.compound} · ${stint.number_of_laps} voltas`}
          >
            {widthPercent > 6 ? (
              <span>
                {getCompoundLabel(stint.compound)} · {stint.number_of_laps}
              </span>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
