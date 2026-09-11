/**
 * Concateneaza clase conditional. Fara librarie externa (clsx/cva nu sunt in stack).
 * Ultimul castiga doar pentru duplicate exacte; nu rezolva conflicte Tailwind
 * (nu punem doua clase care se bat cap in cap pe acelasi element).
 */
export type ClassValue = string | number | false | null | undefined | ClassValue[]

export function cn(...values: ClassValue[]): string {
  const out: string[] = []
  for (const v of values) {
    if (!v && v !== 0) continue
    if (Array.isArray(v)) {
      const nested = cn(...v)
      if (nested) out.push(nested)
    } else {
      out.push(String(v))
    }
  }
  return out.join(' ')
}
