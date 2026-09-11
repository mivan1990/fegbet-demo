import type { MarketCode, PointsMap, SelectionInput } from '@/api/types'

export const MARKET_LABELS: Record<MarketCode, string> = {
  WINNER: 'Cine câștigă',
  QUALIFY: 'Cine merge mai departe',
  TOTAL_GOALS: 'Total goluri',
  BTTS: 'Ambele echipe marchează',
  SCORER: 'Marcator FEG',
}

/** Cheia de setting pentru punctele unei selecții (oglindă a services/scoring.points_for). */
export function pointsKey(sel: Pick<SelectionInput, 'market' | 'pick' | 'line'>): string {
  switch (sel.market) {
    case 'WINNER':
      return sel.pick === 'DRAW' ? 'pts.winner.draw' : 'pts.winner.side'
    case 'QUALIFY':
      return 'pts.qualify'
    case 'TOTAL_GOALS':
      return `pts.goals.${sel.pick.toLowerCase()}.${sel.line ?? ''}`
    case 'BTTS':
      return sel.pick === 'YES' ? 'pts.btts.yes' : 'pts.btts.no'
    case 'SCORER':
      return 'pts.scorer'
  }
}

export function pointsFor(
  sel: Pick<SelectionInput, 'market' | 'pick' | 'line'>,
  points: PointsMap | undefined,
): number {
  if (!points) return 0
  return points[pointsKey(sel)] ?? 0
}

/** Cheie stabilă pentru o selecție într-un dicționar de UI. */
export function selectionKey(sel: Pick<SelectionInput, 'market' | 'pick' | 'line' | 'player_id'>): string {
  return `${sel.market}:${sel.pick}:${sel.line ?? ''}:${sel.player_id ?? ''}`
}

export const TOTAL_GOALS_LINES = [0.5, 1.5, 2.5, 3.5] as const

interface DescribeContext {
  homeName?: string | null
  awayName?: string | null
  playerNames?: Record<number, string>
}

/** Text lizibil pentru o selecție, afișat pe bilet. */
export function describeSelection(
  sel: Pick<SelectionInput, 'market' | 'pick' | 'line' | 'player_id'>,
  ctx: DescribeContext = {},
): string {
  const side = (pick: string) =>
    pick === 'HOME' ? (ctx.homeName ?? 'Gazde') : pick === 'AWAY' ? (ctx.awayName ?? 'Oaspeți') : 'Egal'
  const line = sel.line != null ? String(sel.line).replace('.', ',') : ''
  switch (sel.market) {
    case 'WINNER':
      return `Câștigător: ${side(sel.pick)}`
    case 'QUALIFY':
      return `Calificare: ${side(sel.pick)}`
    case 'TOTAL_GOALS':
      return `${sel.pick === 'OVER' ? 'Peste' : 'Sub'} ${line} goluri`
    case 'BTTS':
      return `Ambele marchează: ${sel.pick === 'YES' ? 'Da' : 'Nu'}`
    case 'SCORER':
      return `Marcator: ${ctx.playerNames?.[sel.player_id ?? -1] ?? 'jucător FEG'}`
  }
}

/** Descrie ce chip-uri apar pe fiecare piață pentru un meci dat. */
export interface MarketChip {
  label: string
  hint?: string
  sel: SelectionInput
}
