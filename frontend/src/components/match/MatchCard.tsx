import { Link } from 'react-router-dom'
import { ArrowRight, Lock } from 'lucide-react'
import { Badge, Countdown } from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatMatchDateTime } from '@/lib/datetime'
import { useCountdown } from '@/lib/countdown'
import type { Match } from '@/api/types'

function TeamName({ name, isFeg }: { name: string | null; isFeg: boolean }) {
  if (!name) return <span className="text-white/40">TBD</span>
  return (
    <span className={cn('flex min-w-0 items-center gap-2', isFeg && 'text-feg-400')}>
      {isFeg && <span className="h-2 w-2 shrink-0 rounded-full bg-feg-400" aria-hidden />}
      <span className="truncate">{name}</span>
    </span>
  )
}

/** Cele 4 stări din PLAN_SONNET.md secțiunea 4: deschis / urgent / blocat / validat. */
export function MatchCard({ match }: { match: Match }) {
  const settled = match.is_settled
  const locked = match.is_locked && !settled
  const ticket = match.my_ticket
  const { isUrgent } = useCountdown(match.scheduled_at)
  const urgent = !settled && !locked && isUrgent

  return (
    <article
      className={cn(
        'rounded-2xl border bg-navy-900 p-4 shadow-card transition duration-150 md:p-6',
        settled && 'border-white/10',
        locked && 'border-white/10 opacity-70 saturate-50',
        urgent && 'border-bet/40',
        !settled && !locked && !urgent && 'border-white/10',
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex min-w-0 flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wider text-white/45">
          {match.phase === 'GROUP' ? (
            <Badge tone="info">{`Grupa ${match.group_name ?? '?'} · etapa ${match.round_no}`}</Badge>
          ) : (
            <span>{match.stage_label ?? `Runda ${match.round_no}`}</span>
          )}
          {match.scheduled_at && <span>{formatMatchDateTime(match.scheduled_at)}</span>}
        </span>
        {settled ? (
          <Badge tone="neutral">Încheiat</Badge>
        ) : locked ? (
          <Badge tone="neutral">
            <Lock className="h-3 w-3" aria-hidden /> În desfășurare
          </Badge>
        ) : match.scheduled_at ? (
          <Countdown target={match.scheduled_at} />
        ) : (
          <Badge tone="neutral">Neprogramat</Badge>
        )}
      </div>

      <div className="mt-5 flex items-center justify-between gap-4 font-display text-xl md:text-2xl">
        <TeamName name={match.home_team?.name ?? null} isFeg={!!match.home_team?.is_feg} />
        {settled ? (
          <span className="shrink-0 font-mono tabular-nums text-white">
            {match.home_score}
            <span className="mx-1 text-white/30">–</span>
            {match.away_score}
          </span>
        ) : (
          <span className="text-white/30">vs</span>
        )}
        <TeamName name={match.away_team?.name ?? null} isFeg={!!match.away_team?.is_feg} />
      </div>

      <div className="mt-5 flex items-center justify-between gap-3 text-sm">
        {settled && ticket ? (
          <span
            className={cn(
              'inline-flex items-center gap-2 rounded-full px-3 py-1 font-mono text-xs font-semibold',
              (ticket.total_points ?? 0) > 0
                ? 'bg-emerald-500/15 text-emerald-300'
                : 'bg-bet/15 text-bet-400',
            )}
          >
            {(ticket.total_points ?? 0) > 0 ? `+${ticket.total_points} puncte` : '0 puncte'}
          </span>
        ) : ticket && !settled ? (
          <span className="text-white/60">
            Biletul tău: {ticket.selection_count}{' '}
            {ticket.selection_count === 1 ? 'selecție' : 'selecții'} · poți câștiga{' '}
            <span className="font-mono text-fortuna">{ticket.potential_points}p</span>
          </span>
        ) : locked ? (
          <span className="text-white/40">Meciul a început. Biletul e bătut în cuie.</span>
        ) : settled ? (
          <span className="text-white/40">N-ai pariat pe meciul ăsta.</span>
        ) : match.is_bettable ? (
          <span className="text-white/50">N-ai pariat. Curaj!</span>
        ) : (
          <span className="text-white/40">Încă nu se poate paria.</span>
        )}

        {match.is_bettable && (
          <Link
            to={`/meci/${match.id}`}
            className="inline-flex shrink-0 items-center gap-1 font-semibold text-fortuna hover:underline"
          >
            {ticket ? 'Modifică biletul' : 'Pariază'}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        )}
        {(settled || locked) && (
          <Link
            to={`/meci/${match.id}`}
            className="inline-flex shrink-0 items-center gap-1 text-white/50 hover:text-white"
          >
            Detalii <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        )}
      </div>
    </article>
  )
}
