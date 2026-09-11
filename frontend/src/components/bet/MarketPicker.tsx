import type { ReactNode } from 'react'
import { Chip } from '@/components/ui'
import { MARKET_LABELS, TOTAL_GOALS_LINES, pointsFor } from '@/lib/markets'
import type { MarketCode, Match, Player, PointsMap, SelectionInput } from '@/api/types'

interface MarketPickerProps {
  match: Match
  players: Player[]
  points: PointsMap | undefined
  /** Selecția curentă pe fiecare piață (sau undefined). */
  value: Partial<Record<MarketCode, SelectionInput>>
  onToggle: (sel: SelectionInput) => void
  disabled?: boolean
}

function isPicked(
  current: SelectionInput | undefined,
  candidate: SelectionInput,
): boolean {
  if (!current) return false
  return (
    current.pick === candidate.pick &&
    (current.line ?? null) === (candidate.line ?? null) &&
    (current.player_id ?? null) === (candidate.player_id ?? null)
  )
}

function Block({ code, children }: { code: MarketCode; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-navy-900 p-4 md:p-6">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-white/45">
        {MARKET_LABELS[code]}
      </h2>
      {children}
    </section>
  )
}

export function MarketPicker({
  match,
  players,
  points,
  value,
  onToggle,
  disabled = false,
}: MarketPickerProps) {
  const bothTeams = !!match.home_team && !!match.away_team
  const homeName = match.home_team?.name ?? 'Gazde'
  const awayName = match.away_team?.name ?? 'Oaspeți'

  const chip = (sel: SelectionInput, label: string, hint?: string) => (
    <Chip
      label={label}
      hint={hint}
      points={pointsFor(sel, points)}
      selected={isPicked(value[sel.market], sel)}
      disabled={disabled}
      onClick={() => onToggle(sel)}
    />
  )

  return (
    <div className="space-y-3">
      {bothTeams && (
        <Block code="WINNER">
          <div className="grid grid-cols-3 gap-2">
            {chip({ market: 'WINNER', pick: 'HOME' }, homeName)}
            {chip({ market: 'WINNER', pick: 'DRAW' }, 'Egal')}
            {chip({ market: 'WINNER', pick: 'AWAY' }, awayName)}
          </div>
        </Block>
      )}

      {/* La meciurile de grupă, "cine merge mai departe" e pronosticul de grupă — nu piața asta. */}
      {bothTeams && match.phase !== 'GROUP' && (
        <Block code="QUALIFY">
          <div className="grid grid-cols-2 gap-2">
            {chip({ market: 'QUALIFY', pick: 'HOME' }, homeName)}
            {chip({ market: 'QUALIFY', pick: 'AWAY' }, awayName)}
          </div>
        </Block>
      )}

      <Block code="TOTAL_GOALS">
        <p className="mb-2 text-sm text-white/60">Peste</p>
        <div className="grid grid-cols-4 gap-2">
          {TOTAL_GOALS_LINES.map((line) =>
            chip({ market: 'TOTAL_GOALS', pick: 'OVER', line }, 'Peste', String(line).replace('.', ',')),
          )}
        </div>
        <p className="mb-2 mt-4 text-sm text-white/60">Sub</p>
        <div className="grid grid-cols-4 gap-2">
          {TOTAL_GOALS_LINES.map((line) =>
            chip({ market: 'TOTAL_GOALS', pick: 'UNDER', line }, 'Sub', String(line).replace('.', ',')),
          )}
        </div>
      </Block>

      <Block code="BTTS">
        <div className="grid grid-cols-2 gap-2">
          {chip({ market: 'BTTS', pick: 'YES' }, 'Da')}
          {chip({ market: 'BTTS', pick: 'NO' }, 'Nu')}
        </div>
      </Block>

      {/* Piata Marcator apare DOAR la meciurile FEG (nu dezactivata — deloc). */}
      {match.has_feg && players.length > 0 && (
        <Block code="SCORER">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {players.map((p) =>
              chip({ market: 'SCORER', pick: 'SCORER', player_id: p.id }, p.name),
            )}
          </div>
        </Block>
      )}
    </div>
  )
}
