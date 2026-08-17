import { getCompoundColorVar, getCompoundLabel, getCompoundTextColor } from '../theme/compoundColors'

interface TyreIconProps {
  compound: string
  size?: number
  /** Slightly dims + shrinks the ring when this isn't the active choice —
   * used by CompoundPicker for the unselected options. */
  muted?: boolean
}

/** A tyre rendered as a simple ring + colored tread, with the compound's
 * single-letter code in the middle — color is never the only signal. */
export function TyreIcon({ compound, size = 32, muted = false }: TyreIconProps) {
  const fill = getCompoundColorVar(compound)
  const textColor = getCompoundTextColor(compound)

  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full border-4 font-mono font-bold transition-opacity"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.4,
        backgroundColor: fill,
        color: textColor,
        borderColor: 'var(--color-border-strong)',
        opacity: muted ? 0.45 : 1,
      }}
      aria-hidden="true"
    >
      {getCompoundLabel(compound)}
    </span>
  )
}
