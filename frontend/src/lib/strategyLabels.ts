/** Default label for the Nth new strategy: "Estratégia A", "B", "C"...
 * falling back to numbers past Z so it never breaks. */
export function nextStrategyLabel(existingCount: number): string {
  if (existingCount < 26) {
    return `Estratégia ${String.fromCharCode(65 + existingCount)}`
  }
  return `Estratégia ${existingCount + 1}`
}
