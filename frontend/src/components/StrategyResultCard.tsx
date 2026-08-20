import type { NamedStrategy, SafetyCarPeriod, SessionData, StrategyComparisonEntry } from '../api/types'
import { formatDuration } from '../lib/formatTime'
import { estimatePosition, type PositionEstimate } from '../lib/positionEstimate'
import { StrategyBar } from './StrategyBar'

interface StrategyResultCardProps {
  namedStrategy: NamedStrategy
  entry: StrategyComparisonEntry
  isBest: boolean
  session: SessionData
  driverCode: string
  /** Position in the results list — staggers the entrance animation so
   * cards settle in one after another instead of all at once. */
  index: number
}

type Tone = 'positive' | 'negative' | 'neutral'

function timeTone(differenceSeconds: number | null): Tone {
  if (differenceSeconds === null) return 'neutral'
  if (differenceSeconds < -0.05) return 'positive'
  if (differenceSeconds > 0.05) return 'negative'
  return 'neutral'
}

function positionTone(estimate: PositionEstimate): Tone {
  if (!estimate.isComparable || estimate.realPosition === null || estimate.estimatedPosition === null) {
    return 'neutral'
  }
  if (estimate.estimatedPosition < estimate.realPosition) return 'positive'
  if (estimate.estimatedPosition > estimate.realPosition) return 'negative'
  return 'neutral'
}

const TONE_TEXT: Record<Tone, string> = {
  positive: 'text-success',
  negative: 'text-danger',
  neutral: 'text-text-muted',
}

/** "5.3s mais rápida", "5.3s mais lenta", "praticamente igual" — the
 * human-language version of `difference_seconds` (estimated − real; see
 * backend/app/simulation/engine.py). */
function timeDeltaSentence(differenceSeconds: number | null): string {
  if (differenceSeconds === null) return 'sem comparação de tempo disponível'
  const magnitude = Math.abs(differenceSeconds).toFixed(1)
  if (differenceSeconds < -0.05) return `${magnitude}s mais rápida que a estratégia real`
  if (differenceSeconds > 0.05) return `${magnitude}s mais lenta que a estratégia real`
  return 'praticamente igual à estratégia real'
}

/** "Subiria de P10 para P4" / "Manteria a P10" / "Desceria de P4 para P10" —
 * or null when the comparison isn't reliable (see lib/positionEstimate.ts). */
function positionSentence(estimate: PositionEstimate): string | null {
  if (!estimate.isComparable || estimate.realPosition === null || estimate.estimatedPosition === null) {
    return null
  }
  const { realPosition, estimatedPosition } = estimate
  if (estimatedPosition < realPosition) return `Subiria de P${realPosition} para P${estimatedPosition}`
  if (estimatedPosition > realPosition) return `Desceria de P${realPosition} para P${estimatedPosition}`
  return `Manteria a P${realPosition}`
}

function describeSafetyCarPeriod(period: SafetyCarPeriod): string {
  if (period.laps.length === 0) return 'Safety Car / VSC'
  const first = period.laps[0]
  const last = period.laps[period.laps.length - 1]
  const range = first === last ? `volta ${first}` : `voltas ${first}–${last}`
  return `Safety Car / VSC (${range})`
}

function signed(value: number, decimals = 1): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}`
}

/** One simulated strategy told as a small story: the headline moment
 * (position swing, or time gained/lost when the position wouldn't change),
 * how the final time was actually built up (pure pace + safety car), how
 * it stacks up against what really happened, and any caveats — instead of
 * a flat table of numbers. */
export function StrategyResultCard({
  namedStrategy,
  entry,
  isBest,
  session,
  driverCode,
  index,
}: StrategyResultCardProps) {
  const { result } = entry

  // An INCOMPLETE estimate (some stint excluded for lack of pace data)
  // covers fewer laps than the strategy planned — comparing that against
  // the real (full-race) time, or using it for a position estimate,
  // would compare different distances and produce nonsense (e.g. a
  // strategy missing a 15-lap stint reading as "-1477s, jumps to P1").
  // The backend already refuses to compute difference_seconds for these
  // (is_complete_estimate=false), but the position estimate is derived
  // client-side, so it has to be gated here too — never call
  // estimatePosition for an incomplete result.
  if (!result.is_complete_estimate) {
    return (
      <IncompleteStrategyResultCard
        namedStrategy={namedStrategy}
        entry={entry}
        session={session}
        index={index}
      />
    )
  }

  const estimate = estimatePosition(session, driverCode, result.estimated_total_time_seconds)

  const positionChanged =
    estimate.isComparable && estimate.realPosition !== null && estimate.estimatedPosition !== null &&
    estimate.realPosition !== estimate.estimatedPosition

  const heroTone = positionChanged ? positionTone(estimate) : timeTone(result.difference_seconds)
  const sentence = positionSentence(estimate)

  const pureRaceSeconds =
    result.estimated_total_time_seconds !== null
      ? result.estimated_total_time_seconds - result.safety_car_time_added_seconds
      : null

  return (
    <div
      className={
        isBest
          ? 'animate-result-in relative flex flex-col gap-6 overflow-hidden rounded-xl border border-accent bg-gradient-to-br from-accent/15 via-surface to-surface p-6 shadow-[0_0_0_1px_rgba(255,45,63,0.15),0_24px_48px_-28px_rgba(255,45,63,0.5)] backdrop-blur-sm sm:p-7'
          : 'animate-result-in flex flex-col gap-6 rounded-xl border border-border bg-surface/90 p-6 backdrop-blur-sm sm:p-7'
      }
      style={{ animationDelay: `${index * 70}ms` }}
    >
      {isBest && (
        <div
          className="pointer-events-none absolute -right-11 top-5 w-40 rotate-45 bg-accent py-1 text-center text-[11px] font-bold tracking-widest text-white uppercase shadow-md"
          aria-hidden="true"
        >
          Mais rápida
        </div>
      )}

      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-lg font-semibold text-text">{entry.label}</h3>
          {isBest && (
            <span className="rounded-full bg-accent/15 px-3 py-1 text-xs font-semibold text-accent">
              🏆 Melhor tempo estimado
            </span>
          )}
        </div>
        <StrategyBar strategy={namedStrategy.strategy} raceTotalLaps={session.total_laps} />
      </div>

      {/* Hero: the one number that matters most for this strategy. */}
      <div className="border-y border-border/60 py-5">
        {positionChanged && estimate.realPosition !== null && estimate.estimatedPosition !== null ? (
          <div className="flex flex-wrap items-baseline gap-3 sm:gap-4">
            <span className="font-mono text-2xl text-text-dim sm:text-3xl">P{estimate.realPosition}</span>
            <span className={`text-3xl leading-none sm:text-4xl ${TONE_TEXT[heroTone]}`} aria-hidden="true">
              →
            </span>
            <span className={`font-mono text-5xl leading-none font-black sm:text-6xl ${TONE_TEXT[heroTone]}`}>
              P{estimate.estimatedPosition}
            </span>
          </div>
        ) : (
          <p className={`font-mono text-5xl leading-none font-black sm:text-6xl ${TONE_TEXT[heroTone]}`}>
            {result.difference_seconds !== null ? signed(result.difference_seconds) : '—'}
            {result.difference_seconds !== null && <span className="text-3xl sm:text-4xl">s</span>}
          </p>
        )}

        <p className="mt-3 text-lg font-medium text-text">
          {sentence ??
            (result.estimated_total_time_seconds === null
              ? 'Sem tempo estimado para esta estratégia.'
              : 'Posição estimada não disponível para este piloto.')}
        </p>
        <p className="mt-1 text-sm text-text-muted">
          {sentence ? timeDeltaSentence(result.difference_seconds) : (estimate.reason ?? '')}
        </p>
      </div>

      {/* How the final time was built up — not just the end number. */}
      {result.estimated_total_time_seconds !== null && (
        <div className="flex flex-col gap-4 sm:flex-row sm:gap-8">
          <div className="flex-1">
            <p className="text-xs font-semibold tracking-wide text-text-dim uppercase">Como chegámos a este tempo</p>
            <dl className="mt-2 flex flex-col gap-1.5 font-mono text-sm">
              <div className="flex items-baseline justify-between gap-4">
                <dt className="text-text-muted">Ritmo de corrida estimado</dt>
                <dd className="text-text">{pureRaceSeconds !== null ? formatDuration(pureRaceSeconds) : '—'}</dd>
              </div>
              {result.safety_car_periods.map((period, periodIndex) => (
                <div key={periodIndex} className="flex items-baseline justify-between gap-4">
                  <dt className="text-text-muted">{describeSafetyCarPeriod(period)}</dt>
                  <dd className="text-warning">{signed(period.time_lost_seconds)}s</dd>
                </div>
              ))}
              <div className="flex items-baseline justify-between gap-4 border-t border-border pt-1.5 font-semibold">
                <dt className="text-text">Tempo final estimado</dt>
                <dd className="text-text">{formatDuration(result.estimated_total_time_seconds)}</dd>
              </div>
            </dl>
          </div>

          <div className="flex-1">
            <p className="text-xs font-semibold tracking-wide text-text-dim uppercase">Vs. a estratégia real</p>
            <dl className="mt-2 flex flex-col gap-1.5 font-mono text-sm">
              <div className="flex items-baseline justify-between gap-4">
                <dt className="text-text-muted">Estratégia real</dt>
                <dd className="text-text">
                  {result.real_total_time_seconds !== null ? formatDuration(result.real_total_time_seconds) : '—'}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-4">
                <dt className="text-text-muted">Esta estratégia</dt>
                <dd className="text-text">{formatDuration(result.estimated_total_time_seconds)}</dd>
              </div>
              <div className="flex items-baseline justify-between gap-4 border-t border-border pt-1.5 font-semibold">
                <dt className="text-text">Diferença</dt>
                <dd className={TONE_TEXT[timeTone(result.difference_seconds)]}>
                  {result.difference_seconds !== null ? (
                    <span className="inline-flex items-center gap-1.5">
                      {signed(result.difference_seconds)}s
                      <span aria-hidden="true">
                        {timeTone(result.difference_seconds) === 'positive'
                          ? '✓'
                          : timeTone(result.difference_seconds) === 'negative'
                            ? '✕'
                            : '='}
                      </span>
                    </span>
                  ) : (
                    '—'
                  )}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div className="flex flex-col gap-2 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3">
          {result.warnings.map((warning, warningIndex) => (
            <p key={warningIndex} className="flex items-start gap-2 text-sm text-text">
              <span className="mt-0.5 text-warning" aria-hidden="true">
                ⚠
              </span>
              <span>{warning}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

interface IncompleteStrategyResultCardProps {
  namedStrategy: NamedStrategy
  entry: StrategyComparisonEntry
  session: SessionData
  index: number
}

/** An estimate that skipped one or more stints for lack of pace data.
 * Deliberately has NO hero number, NO time delta, NO position badge, and
 * can never carry the "MAIS RÁPIDA" ribbon (the backend already excludes
 * it from `best_label` — see comparison.py) — any of those would compare
 * a partial-distance estimate against the real (full-race) time, which
 * is exactly the bug this card exists to avoid. */
function IncompleteStrategyResultCard({
  namedStrategy,
  entry,
  session,
  index,
}: IncompleteStrategyResultCardProps) {
  const { result } = entry
  const missingLaps = result.strategy_total_laps - result.estimated_laps_covered

  return (
    <div
      className="animate-result-in flex flex-col gap-6 rounded-xl border border-warning/40 bg-surface/90 p-6 backdrop-blur-sm sm:p-7"
      style={{ animationDelay: `${index * 70}ms` }}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-lg font-semibold text-text">{entry.label}</h3>
          <span className="rounded-full bg-warning/15 px-3 py-1 text-xs font-semibold text-warning">
            Estimativa incompleta
          </span>
        </div>
        <StrategyBar strategy={namedStrategy.strategy} raceTotalLaps={session.total_laps} />
      </div>

      <div className="border-y border-border/60 py-5">
        <p className="flex items-start gap-2 text-lg font-medium text-text">
          <span className="mt-0.5 text-warning" aria-hidden="true">
            ⚠
          </span>
          <span>
            Faltam dados de ritmo para {missingLaps} de {result.strategy_total_laps} voltas
            planeadas.
          </span>
        </p>
        <p className="mt-2 text-sm text-text-muted">
          Sem esses dados, o tempo estimado cobriria menos voltas do que a corrida real — por
          isso não mostramos tempo, diferença nem posição estimada para esta estratégia (só
          seriam comparações enganosas). Ajusta o composto do stint em falta para tentar de
          novo.
        </p>
      </div>

      {result.warnings.length > 0 && (
        <div className="flex flex-col gap-2 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3">
          {result.warnings.map((warning, warningIndex) => (
            <p key={warningIndex} className="flex items-start gap-2 text-sm text-text">
              <span className="mt-0.5 text-warning" aria-hidden="true">
                ⚠
              </span>
              <span>{warning}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
