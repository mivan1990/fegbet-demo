import { Trash2 } from 'lucide-react'
import { Button, TicketStub } from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatMatchDateTime } from '@/lib/datetime'
import { describeSelection, pointsFor } from '@/lib/markets'
import { ticketCode } from '@/lib/ticket'
import type { Match, PointsMap, SelectionInput } from '@/api/types'

interface BetSlipProps {
  match: Match
  selections: SelectionInput[]
  points: PointsMap | undefined
  playerNames: Record<number, string>
  existingTicketId: number | null
  disabled?: boolean
  saving?: boolean
  deleting?: boolean
  onSave: () => void
  onDelete: () => void
}

export function BetSlip({
  match,
  selections,
  points,
  playerNames,
  existingTicketId,
  disabled = false,
  saving = false,
  deleting = false,
  onSave,
  onDelete,
}: BetSlipProps) {
  const total = selections.reduce((sum, s) => sum + pointsFor(s, points), 0)
  const ctx = {
    homeName: match.home_team?.name,
    awayName: match.away_team?.name,
    playerNames,
  }

  return (
    <div className="flex flex-col">
      <TicketStub>
        <div className="border-b border-dashed border-ink/20 px-4 py-3 text-center">
          <p className="font-display text-sm tracking-wide">
            FEG<span className="text-bet">BET</span> · {ticketCode(existingTicketId)}
          </p>
          <p className="mt-1 text-xs text-ink/60">
            {match.home_team?.name ?? 'Gazde'} vs {match.away_team?.name ?? 'Oaspeți'}
          </p>
          {match.scheduled_at && (
            <p className="text-xs text-ink/50">{formatMatchDateTime(match.scheduled_at)}</p>
          )}
        </div>

        <div className="px-4 py-3">
          {selections.length === 0 ? (
            <p className="py-4 text-center text-sm text-ink/50">
              Alege selecții din stânga ca să-ți construiești biletul.
            </p>
          ) : (
            <ul className="space-y-2">
              {selections.map((s, i) => (
                <li
                  key={`${s.market}-${i}`}
                  className="flex items-center justify-between gap-3 text-sm"
                >
                  <span>{describeSelection(s, ctx)}</span>
                  <span className="shrink-0 font-mono text-ink/70">
                    +{pointsFor(s, points)}p
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="border-t border-dashed border-ink/20 px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-ink/60">
              Poți câștiga
            </span>
            <span className="font-mono text-xl font-bold tabular-nums">{total}p</span>
          </div>
        </div>
      </TicketStub>

      <div className="mt-4 flex flex-col gap-2">
        <Button
          variant="primary"
          size="lg"
          block
          disabled={disabled || selections.length === 0}
          loading={saving}
          onClick={onSave}
        >
          {existingTicketId ? 'ACTUALIZEAZĂ BILETUL' : 'BAG BILETUL'}
        </Button>
        {existingTicketId && (
          <Button
            variant="ghost"
            block
            disabled={disabled}
            loading={deleting}
            iconLeft={<Trash2 className="h-4 w-4" />}
            onClick={onDelete}
            className={cn('text-bet-400 hover:text-bet-400')}
          >
            Șterge biletul
          </Button>
        )}
      </div>
    </div>
  )
}
