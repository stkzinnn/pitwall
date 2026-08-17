import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { getDrivers } from '../api/races'
import { compareStrategies } from '../api/simulation'
import type { ComparisonResult, DriverInfo, NamedStrategy, SessionData, StintPlan } from '../api/types'
import { DriverCard } from '../components/DriverCard'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { StrategyEditor } from '../components/StrategyEditor'
import { StrategyResultCard } from '../components/StrategyResultCard'
import { useRaceSession } from '../hooks/useRaceSession'
import { nextStrategyLabel } from '../lib/strategyLabels'
import { ROUTES, raceResultsPath } from '../routes/paths'

type ComparisonStatus = 'idle' | 'loading' | 'error' | 'success'

const DEFAULT_NEW_STINT: StintPlan = { compound: 'SOFT', number_of_laps: 10 }

function initialStrategies(): NamedStrategy[] {
  return [{ label: nextStrategyLabel(0), strategy: [] }]
}

export function StrategyBuilderPage() {
  const params = useParams<{ year: string; round: string; driver: string }>()
  const year = Number(params.year)
  const round = Number(params.round)
  const driverCode = params.driver ?? ''

  const { status, session, errorMessage } = useRaceSession(year, round)
  const [strategies, setStrategies] = useState<NamedStrategy[]>(initialStrategies)
  const [comparisonStatus, setComparisonStatus] = useState<ComparisonStatus>('idle')
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null)
  const [comparisonError, setComparisonError] = useState('')

  const canSimulate = strategies.some((strategy) => strategy.strategy.length > 0)

  async function handleSimulate() {
    setComparisonStatus('loading')
    setComparisonError('')
    try {
      const result = await compareStrategies(driverCode, year, round, strategies)
      setComparisonResult(result)
      setComparisonStatus('success')
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.detail ?? 'O servidor não conseguiu simular estas estratégias.')
          : 'Não foi possível ligar ao servidor.'
      setComparisonError(message)
      setComparisonStatus('error')
    }
  }

  function addStrategy() {
    setStrategies((current) => [...current, { label: nextStrategyLabel(current.length), strategy: [] }])
  }

  function removeStrategy(strategyIndex: number) {
    setStrategies((current) => current.filter((_, index) => index !== strategyIndex))
  }

  function updateStrategyLabel(strategyIndex: number, label: string) {
    setStrategies((current) =>
      current.map((strategy, index) => (index === strategyIndex ? { ...strategy, label } : strategy)),
    )
  }

  function addStint(strategyIndex: number) {
    setStrategies((current) =>
      current.map((strategy, index) =>
        index === strategyIndex
          ? { ...strategy, strategy: [...strategy.strategy, { ...DEFAULT_NEW_STINT }] }
          : strategy,
      ),
    )
  }

  function updateStint(strategyIndex: number, stintIndex: number, patch: Partial<StintPlan>) {
    setStrategies((current) =>
      current.map((strategy, index) => {
        if (index !== strategyIndex) return strategy
        return {
          ...strategy,
          strategy: strategy.strategy.map((stint, sIndex) =>
            sIndex === stintIndex ? { ...stint, ...patch } : stint,
          ),
        }
      }),
    )
  }

  function removeStint(strategyIndex: number, stintIndex: number) {
    setStrategies((current) =>
      current.map((strategy, index) =>
        index === strategyIndex
          ? { ...strategy, strategy: strategy.strategy.filter((_, sIndex) => sIndex !== stintIndex) }
          : strategy,
      ),
    )
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <Link
          to={ROUTES.raceSelection}
          className="inline-flex items-center gap-1.5 text-text-muted transition-colors hover:text-accent"
        >
          ← Voltar à seleção de corrida
        </Link>
        {Number.isFinite(year) && Number.isFinite(round) && (
          <Link
            to={raceResultsPath(year, round)}
            className="inline-flex items-center gap-1.5 text-text-muted transition-colors hover:text-accent"
          >
            Ver classificação da corrida
          </Link>
        )}
      </div>

      {status === 'loading' && (
        <LoadingState message="A carregar dados da sessão…" hint="Um instante." />
      )}

      {status === 'error' && <ErrorState message={errorMessage} />}

      {status === 'success' && session && (
        <StrategyBuilderContent
          session={session}
          driverCode={driverCode}
          strategies={strategies}
          onAddStrategy={addStrategy}
          onRemoveStrategy={removeStrategy}
          onUpdateStrategyLabel={updateStrategyLabel}
          onAddStint={addStint}
          onUpdateStint={updateStint}
          onRemoveStint={removeStint}
          canSimulate={canSimulate}
          comparisonStatus={comparisonStatus}
          comparisonResult={comparisonResult}
          comparisonError={comparisonError}
          onSimulate={handleSimulate}
        />
      )}
    </div>
  )
}

interface StrategyBuilderContentProps {
  session: SessionData
  driverCode: string
  strategies: NamedStrategy[]
  onAddStrategy: () => void
  onRemoveStrategy: (strategyIndex: number) => void
  onUpdateStrategyLabel: (strategyIndex: number, label: string) => void
  onAddStint: (strategyIndex: number) => void
  onUpdateStint: (strategyIndex: number, stintIndex: number, patch: Partial<StintPlan>) => void
  onRemoveStint: (strategyIndex: number, stintIndex: number) => void
  canSimulate: boolean
  comparisonStatus: ComparisonStatus
  comparisonResult: ComparisonResult | null
  comparisonError: string
  onSimulate: () => void
}

function StrategyBuilderContent({
  session,
  driverCode,
  strategies,
  onAddStrategy,
  onRemoveStrategy,
  onUpdateStrategyLabel,
  onAddStint,
  onUpdateStint,
  onRemoveStint,
  canSimulate,
  comparisonStatus,
  comparisonResult,
  comparisonError,
  onSimulate,
}: StrategyBuilderContentProps) {
  const driver: DriverInfo = getDrivers(session).find((candidate) => candidate.code === driverCode) ?? {
    code: driverCode,
    full_name: null,
    number: null,
    team_name: null,
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-5 rounded-xl border border-border bg-surface p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <p className="font-mono text-sm tracking-widest text-text-dim uppercase">
            {session.year} · Ronda {session.round}
            {session.total_laps !== null && ` · ${session.total_laps} voltas`}
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-text">
            {session.event_name ?? 'Corrida'}
          </h1>
          <p className="mt-1 text-sm text-text-muted">Construtor de estratégia</p>
        </div>

        <div className="w-full sm:w-80">
          <DriverCard driver={driver} />
        </div>
      </div>

      <div className="flex flex-col gap-5">
        {strategies.map((strategy, index) => (
          <StrategyEditor
            key={index}
            strategy={strategy}
            raceTotalLaps={session.total_laps}
            onLabelChange={(label) => onUpdateStrategyLabel(index, label)}
            onAddStint={() => onAddStint(index)}
            onUpdateStint={(stintIndex, patch) => onUpdateStint(index, stintIndex, patch)}
            onRemoveStint={(stintIndex) => onRemoveStint(index, stintIndex)}
            onRemoveStrategy={() => onRemoveStrategy(index)}
          />
        ))}

        {strategies.length === 0 && (
          <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-text-dim">
            Nenhuma estratégia — adiciona uma para começar.
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onAddStrategy}
            className="self-start rounded-md bg-accent px-5 py-2.5 font-medium text-bg transition-colors hover:bg-accent-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            + Adicionar estratégia
          </button>

          <button
            type="button"
            onClick={onSimulate}
            disabled={!canSimulate || comparisonStatus === 'loading'}
            className="self-start rounded-md border border-accent px-5 py-2.5 font-medium text-accent transition-colors hover:bg-accent hover:text-bg disabled:cursor-not-allowed disabled:border-border disabled:text-text-dim disabled:hover:bg-transparent"
          >
            {comparisonStatus === 'loading' ? 'A simular…' : 'Simular estratégias'}
          </button>

          {!canSimulate && (
            <p className="text-xs text-text-dim">Adiciona pelo menos um stint a uma estratégia para simular.</p>
          )}
        </div>
      </div>

      {comparisonStatus === 'error' && <ErrorState message={comparisonError} />}

      {comparisonStatus === 'loading' && (
        <LoadingState message="A simular estratégias…" hint="A correr o motor de simulação para cada estratégia." />
      )}

      {comparisonStatus === 'success' && comparisonResult && (
        <div className="flex flex-col gap-6">
          <div>
            <h2 className="text-2xl font-semibold text-text">Resultados da simulação</h2>
            <p className="mt-2 flex items-start gap-2 max-w-3xl text-sm text-text-muted">
              <span className="mt-0.5 text-accent" aria-hidden="true">
                📻
              </span>
              <span>
                Cenário: só {driverCode} muda de estratégia — todos os outros pilotos repetem exatamente a
                corrida real. É a pergunta "e se só ele tivesse corrido assim?", não uma nova corrida
                inteira. Por isso, pilotos que na realidade ficaram em atraso ou abandonaram ficam fora do
                recálculo de posições (a razão aparece em cada caso).
              </span>
            </p>
          </div>

          <div className="flex flex-col gap-6">
            {comparisonResult.strategies.map((entry, index) => {
              const namedStrategy = strategies.find((strategy) => strategy.label === entry.label) ??
                strategies[index] ?? { label: entry.label, strategy: [] }
              return (
                <StrategyResultCard
                  key={entry.label}
                  namedStrategy={namedStrategy}
                  entry={entry}
                  isBest={comparisonResult.best_label === entry.label}
                  session={session}
                  driverCode={driverCode}
                  index={index}
                />
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
