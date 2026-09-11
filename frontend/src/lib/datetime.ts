/**
 * Datele vin de la server ca ISO 8601 UTC (timezone-aware).
 * In UI se afiseaza mereu in fusul Europe/Bucharest.
 */

const TZ = 'Europe/Bucharest'

const DAYS_SHORT = ['DUM', 'LUN', 'MAR', 'MIE', 'JOI', 'VIN', 'SÂM']
const MONTHS_SHORT = [
  'ian', 'feb', 'mar', 'apr', 'mai', 'iun',
  'iul', 'aug', 'sept', 'oct', 'noi', 'dec',
]

export function parseUtc(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

/** Parti calendaristice ale unei date, in fusul Bucuresti. */
function partsInBucharest(d: Date) {
  const fmt = new Intl.DateTimeFormat('ro-RO', {
    timeZone: TZ,
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
  const map: Record<string, string> = {}
  for (const p of fmt.formatToParts(d)) map[p.type] = p.value
  return map
}

/** Ex: "SÂM 14 sept · 18:30" */
export function formatMatchDateTime(iso: string | null | undefined): string {
  const d = parseUtc(iso)
  if (!d) return 'Data nestabilita'
  const jsDay = new Date(d.toLocaleString('en-US', { timeZone: TZ }))
  const weekday = DAYS_SHORT[jsDay.getDay()]
  const day = jsDay.getDate()
  const month = MONTHS_SHORT[jsDay.getMonth()]
  const p = partsInBucharest(d)
  return `${weekday} ${day} ${month} · ${p.hour}:${p.minute}`
}

/** Ex: "18:30" */
export function formatTime(iso: string | null | undefined): string {
  const d = parseUtc(iso)
  if (!d) return '--:--'
  const p = partsInBucharest(d)
  return `${p.hour}:${p.minute}`
}

/** Ex: "14 sept 2025, 18:30" — pentru loguri si detalii. */
export function formatFull(iso: string | null | undefined): string {
  const d = parseUtc(iso)
  if (!d) return '—'
  return new Intl.DateTimeFormat('ro-RO', {
    timeZone: TZ,
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(d)
}

/** Ex: "incepe in 2 zile 4 ore" / "a inceput" */
export function formatRelativeToNow(iso: string | null | undefined, now: number = Date.now()): string {
  const d = parseUtc(iso)
  if (!d) return 'fara data'
  const diff = d.getTime() - now
  if (diff <= 0) return 'a inceput'

  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(mins / 60)
  const days = Math.floor(hours / 24)

  if (days >= 1) {
    const remHours = hours - days * 24
    return `incepe in ${days} ${days === 1 ? 'zi' : 'zile'}${remHours ? ` ${remHours} ${remHours === 1 ? 'ora' : 'ore'}` : ''}`
  }
  if (hours >= 1) {
    const remMins = mins - hours * 60
    return `incepe in ${hours} ${hours === 1 ? 'ora' : 'ore'}${remMins ? ` ${remMins} min` : ''}`
  }
  return `incepe in ${mins} min`
}
