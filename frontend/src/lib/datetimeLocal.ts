/**
 * Conversii pentru `<input type="datetime-local">`.
 * Input-ul lucreaza in ora locala a browser-ului (adminul e in Romania).
 * Serverul primeste/da mereu ISO UTC.
 */

/** ISO UTC -> "YYYY-MM-DDTHH:mm" in ora locala, pentru valoarea input-ului. */
export function isoToLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** "YYYY-MM-DDTHH:mm" (ora locala) -> ISO UTC. String gol -> null. */
export function localInputToIso(value: string): string | null {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  return d.toISOString()
}
