interface LogoProps {
  size?: number
  className?: string
}

/** The PitWall mark: a "P" set inside a panel (the pit wall itself), with
 * an accent dot standing in for the car/timing signal — SVG inline, in
 * the brand red, with a subtle glow. No external image asset, so it
 * scales crisply and recolors for free if the theme ever changes. */
export function Logo({ size = 32, className }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <filter id="pitwall-logo-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <rect
        x="1.5"
        y="1.5"
        width="29"
        height="29"
        rx="7"
        fill="var(--color-surface-raised)"
        stroke="var(--color-accent)"
        strokeWidth="1.5"
      />

      <path
        d="M11 8.5h7.2a5 5 0 0 1 0 10H14v5h-3v-15Zm3 3v4h4a2 2 0 0 0 0-4h-4Z"
        fill="var(--color-text)"
      />

      <circle cx="23.5" cy="9" r="2.4" fill="var(--color-accent)" filter="url(#pitwall-logo-glow)" />
    </svg>
  )
}
