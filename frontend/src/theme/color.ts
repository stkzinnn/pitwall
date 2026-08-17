/** Picks readable text (near-black or white) for a given background hex,
 * via a quick relative-luminance estimate — good enough for avatar/badge
 * text, not a full WCAG contrast solver. Shared by teamColors.ts and
 * compoundColors.ts so both use the same readability rule. */
export function readableTextColor(backgroundHex: string): '#0a0d12' | '#f5f7fa' {
  const hex = backgroundHex.replace('#', '')
  const r = parseInt(hex.slice(0, 2), 16) / 255
  const g = parseInt(hex.slice(2, 4), 16) / 255
  const b = parseInt(hex.slice(4, 6), 16) / 255
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return luminance > 0.6 ? '#0a0d12' : '#f5f7fa'
}
