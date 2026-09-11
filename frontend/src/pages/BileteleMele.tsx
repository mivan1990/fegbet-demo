import { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Ticket as TicketIcon } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Badge, Button, EmptyState, Skeleton, Stamp, TicketStub } from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatMatchDateTime } from '@/lib/datetime'
import { describeSelection } from '@/lib/markets'
import { ticketCode, ticketVerdict, groupPredictionVerdict } from '@/lib/ticket'
import { celebrateTicketOnce, celebrateGroupPredictionOnce } from '@/lib/confetti'
import { useMyTickets } from '@/api/tickets'
import { useGroups, useMyGroupPredictions } from '@/api/groups'
import type { GroupPrediction, Ticket } from '@/api/types'

function statusBadge(t: Ticket) {
  if (t.status !== 'SETTLED') return <Badge tone="info">Deschis</Badge>
  const pts = t.total_points ?? 0
  if (pts > 0) return <Badge tone="success">+{pts}p</Badge>
  return <Badge tone="urgent">0p</Badge>
}

function groupPredictionStatusBadge(p: GroupPrediction) {
  if (p.status !== 'SETTLED') return <Badge tone="info">Deschis</Badge>
  const pts = p.total_points ?? 0
  if (pts > 0) return <Badge tone="success">+{pts}p</Badge>
  return <Badge tone="urgent">0p</Badge>
}

function GroupPredictionCard({ p, groupName }: { p: GroupPrediction; groupName: string }) {
  const verdict = groupPredictionVerdict(p)

  useEffect(() => {
    if (verdict === 'won') celebrateGroupPredictionOnce(p.id)
  }, [verdict, p.id])

  return (
    <TicketStub overlay={verdict ? <Stamp verdict={verdict} /> : undefined}>
      <header className="flex items-center justify-between gap-3 border-b border-dashed border-ink/20 px-4 py-3">
        <div>
          <p className="font-display text-sm">
            FEG<span className="text-bet">BET</span> · {ticketCode(p.id)}
          </p>
          <p className="text-xs text-ink/60">Grupa {groupName} · cine merge mai departe</p>
        </div>
        {groupPredictionStatusBadge(p)}
      </header>

      <ul className="divide-y divide-ink/10 px-4">
        {p.picks.map((pick) => (
          <li key={pick.team_id} className="flex items-center justify-between gap-3 py-2 text-sm">
            <span
              className={cn(
                pick.is_correct === true && 'font-medium text-emerald-700',
                pick.is_correct === false && 'text-ink/40 line-through',
              )}
            >
              {pick.team_name}
            </span>
            <span className="shrink-0 font-mono text-ink/70">
              {p.status === 'SETTLED' ? (pick.is_correct ? `+${pick.points_awarded}p` : '0p') : ''}
            </span>
          </li>
        ))}
      </ul>

      <footer className="flex items-center justify-between gap-3 border-t border-dashed border-ink/20 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-ink/60">
          {p.status === 'SETTLED' ? 'Total' : 'Poți câștiga'}
        </span>
        <span className="font-mono text-lg font-bold tabular-nums">
          {p.status === 'SETTLED' ? (p.total_points ?? 0) : p.potential_points}p
        </span>
      </footer>

      {p.status !== 'SETTLED' && (
        <div className="border-t border-dashed border-ink/20 px-4 py-3">
          <Link to="/grupe">
            <Button variant="secondary" size="sm" block>
              Vezi grupa
            </Button>
          </Link>
        </div>
      )}
    </TicketStub>
  )
}

function TicketCard({ t }: { t: Ticket }) {
  const m = t.match
  const verdict = ticketVerdict(t)
  const playerNames: Record<number, string> = Object.fromEntries(
    t.selections
      .filter((s) => s.player_id != null && s.player_name != null)
      .map((s) => [s.player_id as number, s.player_name as string]),
  )

  return (
    <TicketStub overlay={verdict ? <Stamp verdict={verdict} /> : undefined}>
      <header className="flex items-center justify-between gap-3 border-b border-dashed border-ink/20 px-4 py-3">
        <div>
          <p className="font-display text-sm">
            FEG<span className="text-bet">BET</span> · {ticketCode(t.id)}
          </p>
          <p className="text-xs text-ink/60">
            {m?.home_name ?? 'TBD'} vs {m?.away_name ?? 'TBD'}
            {m?.scheduled_at && <> · {formatMatchDateTime(m.scheduled_at)}</>}
          </p>
        </div>
        {statusBadge(t)}
      </header>

      <ul className="divide-y divide-ink/10 px-4">
        {t.selections.map((s, i) => (
          <li key={i} className="flex items-center justify-between gap-3 py-2 text-sm">
            <span
              className={cn(
                s.is_correct === true && 'font-medium text-emerald-700',
                s.is_correct === false && 'text-ink/40 line-through',
              )}
            >
              {describeSelection(s, {
                homeName: m?.home_name,
                awayName: m?.away_name,
                playerNames,
              })}
            </span>
            <span className="shrink-0 font-mono text-ink/70">
              {t.status === 'SETTLED'
                ? s.is_correct
                  ? `+${s.points_awarded}p`
                  : '0p'
                : `+${s.points}p`}
            </span>
          </li>
        ))}
      </ul>

      <footer className="flex items-center justify-between gap-3 border-t border-dashed border-ink/20 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-ink/60">
          {t.status === 'SETTLED' ? 'Total' : 'Poți câștiga'}
        </span>
        <span className="font-mono text-lg font-bold tabular-nums">
          {t.status === 'SETTLED' ? (t.total_points ?? 0) : t.potential_points}p
        </span>
      </footer>

      {t.status !== 'SETTLED' && m && !m.is_locked && (
        <div className="border-t border-dashed border-ink/20 px-4 py-3">
          <Link to={`/meci/${t.match_id}`}>
            <Button variant="secondary" size="sm" block>
              Mai schimb o dată, că am o presimțire
            </Button>
          </Link>
        </div>
      )}
    </TicketStub>
  )
}

export function BileteleMele() {
  const { data, isLoading, isError } = useMyTickets()
  const { data: groupPredictions } = useMyGroupPredictions()
  const { data: groups } = useGroups()

  const groupNameById = useMemo(
    () => Object.fromEntries((groups ?? []).map((g) => [g.id, g.name])),
    [groups],
  )

  const open = (data ?? []).filter((t) => t.status !== 'SETTLED')
  const settled = (data ?? []).filter((t) => t.status === 'SETTLED')
  const totalPoints = settled.reduce((s, t) => s + (t.total_points ?? 0), 0)

  // Confetti o singură dată pentru primul bilet câștigător nevăzut.
  useEffect(() => {
    const firstWin = settled.find((t) => (t.total_points ?? 0) > 0)
    if (firstWin) celebrateTicketOnce(firstWin.id)
  }, [settled])

  return (
    <>
      <PageHeader
        title="Biletele mele"
        subtitle={
          settled.length > 0
            ? `${totalPoints} puncte strânse din ${settled.length} bilete decontate.`
            : 'Istoricul tău de pariuri.'
        }
      />

      {(groupPredictions ?? []).length > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 font-display text-lg text-white">Pronosticuri pe grupe</h2>
          <div className="space-y-4">
            {(groupPredictions ?? []).map((p) => (
              <GroupPredictionCard key={p.id} p={p} groupName={groupNameById[p.group_id] ?? '?'} />
            ))}
          </div>
        </section>
      )}

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-48 w-full" rounded="2xl" />
          <Skeleton className="h-48 w-full" rounded="2xl" />
        </div>
      ) : isError ? (
        <EmptyState icon={TicketIcon} title="Am pierdut mingea" line="Nu am putut încărca biletele. Mai încearcă." />
      ) : (data ?? []).length === 0 ? (
        <EmptyState
          icon={TicketIcon}
          title="N-ai niciun bilet"
          line="N-ai pariat pe nimic încă. Curaj!"
          action={
            <Link to="/meciuri">
              <Button variant="primary">Vezi meciurile</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-8">
          {open.length > 0 && (
            <section>
              <h2 className="mb-3 font-display text-lg text-white">Deschise</h2>
              <div className="space-y-4">
                {open.map((t) => (
                  <TicketCard key={t.id} t={t} />
                ))}
              </div>
            </section>
          )}
          {settled.length > 0 && (
            <section>
              <h2 className="mb-3 font-display text-lg text-white">Decontate</h2>
              <div className="space-y-4">
                {settled.map((t) => (
                  <TicketCard key={t.id} t={t} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  )
}
