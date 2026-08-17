import type { NamedStrategy, StintPlan } from '../api/types'
import { StintEditor } from './StintEditor'
import { StrategyBar } from './StrategyBar'

interface StrategyEditorProps {
  strategy: NamedStrategy
  raceTotalLaps: number | null
  onLabelChange: (label: string) => void
  onAddStint: () => void
  onUpdateStint: (index: number, patch: Partial<StintPlan>) => void
  onRemoveStint: (index: number) => void
  onRemoveStrategy: () => void
}

export function StrategyEditor({
  strategy,
  raceTotalLaps,
  onLabelChange,
  onAddStint,
  onUpdateStint,
  onRemoveStint,
  onRemoveStrategy,
}: StrategyEditorProps) {
  const strategyTotalLaps = strategy.strategy.reduce((sum, stint) => sum + stint.number_of_laps, 0)
  const lapDelta = raceTotalLaps === null ? 0 : strategyTotalLaps - raceTotalLaps
  const matchesRaceDistance = raceTotalLaps === null || lapDelta === 0

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <input
          type="text"
          value={strategy.label}
          onChange={(event) => onLabelChange(event.target.value)}
          aria-label="Nome da estratégia"
          className="min-w-0 flex-1 rounded-md border border-transparent bg-transparent px-1 py-1 text-lg font-semibold text-text hover:border-border-strong focus:border-accent focus:bg-surface-raised focus:outline-none"
        />
        <button
          type="button"
          onClick={onRemoveStrategy}
          className="shrink-0 rounded-md px-3 py-1.5 text-sm text-text-dim transition-colors hover:bg-danger/10 hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Remover estratégia
        </button>
      </div>

      <StrategyBar strategy={strategy.strategy} raceTotalLaps={raceTotalLaps} />

      {matchesRaceDistance ? (
        <p className="text-sm text-text-muted">
          {strategyTotalLaps} volta{strategyTotalLaps === 1 ? '' : 's'} planeada
          {strategyTotalLaps === 1 ? '' : 's'}
          {raceTotalLaps !== null && ` / ${raceTotalLaps} da corrida`}
        </p>
      ) : (
        <div className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3">
          <span className="mt-0.5 text-warning" aria-hidden="true">
            ⚠
          </span>
          <p className="text-sm font-medium text-warning">
            {strategyTotalLaps} voltas planeadas vs. {raceTotalLaps} da corrida —{' '}
            {lapDelta > 0
              ? `${lapDelta} volta${lapDelta === 1 ? '' : 's'} a mais vai${lapDelta === 1 ? '' : 'ão'} adicionar tempo de pista que nada tem a ver com a estratégia de pneus.`
              : `faltam ${Math.abs(lapDelta)} volta${Math.abs(lapDelta) === 1 ? '' : 's'} para cobrir a corrida toda — a estimativa fica incompleta.`}
          </p>
        </div>
      )}

      <div className="flex flex-col gap-2 overflow-x-auto">
        {strategy.strategy.map((stint, index) => (
          <StintEditor
            key={index}
            index={index}
            stint={stint}
            onChange={(patch) => onUpdateStint(index, patch)}
            onRemove={() => onRemoveStint(index)}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={onAddStint}
        className="self-start rounded-md border border-dashed border-border-strong px-4 py-2 text-sm font-medium text-text-muted transition-colors hover:border-accent hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        + Adicionar stint
      </button>
    </div>
  )
}
