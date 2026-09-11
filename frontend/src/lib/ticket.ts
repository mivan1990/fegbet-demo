import type { GroupPrediction, Ticket } from '@/api/types'

export type TicketVerdict = 'won' | 'partial' | 'lost'

/** Verdictul unui bilet decontat, pentru stampila. */
export function ticketVerdict(t: Ticket): TicketVerdict | null {
  if (t.status !== 'SETTLED') return null
  const graded = t.selections.filter((s) => s.is_correct != null)
  if (graded.length === 0) return (t.total_points ?? 0) > 0 ? 'won' : 'lost'
  const correct = graded.filter((s) => s.is_correct === true).length
  if (correct === 0) return 'lost'
  if (correct === graded.length) return 'won'
  return 'partial'
}

/** Verdictul unui pronostic de grupă decontat — aceeași convenție ca la bilete. */
export function groupPredictionVerdict(p: GroupPrediction): TicketVerdict | null {
  if (p.status !== 'SETTLED') return null
  const graded = p.picks.filter((pick) => pick.is_correct != null)
  if (graded.length === 0) return (p.total_points ?? 0) > 0 ? 'won' : 'lost'
  const correct = graded.filter((pick) => pick.is_correct === true).length
  if (correct === 0) return 'lost'
  if (correct === graded.length) return 'won'
  return 'partial'
}

/** Codul afisat pe tichet: #FEG-000123. */
export function ticketCode(id: number | null | undefined): string {
  return id ? `#FEG-${String(id).padStart(6, '0')}` : '#FEG-------'
}
