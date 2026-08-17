import { STRATEGY_COMPOUNDS } from '../theme/compoundColors'
import { TyreIcon } from './TyreIcon'

interface CompoundPickerProps {
  value: string
  onChange: (compound: string) => void
  label?: string
}

/** Row of tyre buttons (SOFT/MEDIUM/HARD) — the primary way to set a
 * stint's compound. The selected one is full-size and ringed; the others
 * are muted, so the choice reads at a glance. */
export function CompoundPicker({ value, onChange, label }: CompoundPickerProps) {
  return (
    <div className="flex items-center gap-2">
      {STRATEGY_COMPOUNDS.map((compound) => {
        const isSelected = compound === value
        return (
          <button
            key={compound}
            type="button"
            onClick={() => onChange(compound)}
            aria-pressed={isSelected}
            aria-label={`${label ? `${label}: ` : ''}${compound}`}
            title={compound}
            className={
              isSelected
                ? 'rounded-full ring-2 ring-accent ring-offset-2 ring-offset-surface-raised focus-visible:outline-none'
                : 'rounded-full transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface-raised'
            }
          >
            <TyreIcon compound={compound} muted={!isSelected} />
          </button>
        )
      })}
    </div>
  )
}
