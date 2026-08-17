import type { StintPlan } from '../api/types'
import { CompoundPicker } from './CompoundPicker'

interface StintEditorProps {
  stint: StintPlan
  index: number
  onChange: (patch: Partial<StintPlan>) => void
  onRemove: () => void
}

/** One editable row of a strategy: which compound, for how many laps. */
export function StintEditor({ stint, index, onChange, onRemove }: StintEditorProps) {
  return (
    <div className="flex min-w-[420px] items-center gap-4 rounded-lg border border-border bg-surface px-4 py-3">
      <span className="w-6 shrink-0 font-mono text-sm text-text-dim">{index + 1}</span>

      <CompoundPicker
        label={`Stint ${index + 1}`}
        value={stint.compound}
        onChange={(compound) => onChange({ compound })}
      />

      <div className="flex flex-1 items-center justify-end gap-2">
        <input
          type="number"
          inputMode="numeric"
          min={1}
          max={100}
          value={stint.number_of_laps}
          onChange={(event) => onChange({ number_of_laps: Number(event.target.value) })}
          aria-label={`Voltas do stint ${index + 1}`}
          className="w-20 rounded-md border border-border-strong bg-surface-raised px-2 py-1.5 text-right font-mono text-text focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <span className="text-sm text-text-dim">voltas</span>
      </div>

      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remover stint ${index + 1}`}
        className="shrink-0 rounded-md px-2 py-1 text-text-dim transition-colors hover:bg-danger/10 hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        ✕
      </button>
    </div>
  )
}
