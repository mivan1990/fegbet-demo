import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Lock } from 'lucide-react'
import {
  Badge,
  BottomSheet,
  Countdown,
  EmptyState,
  Skeleton,
  Stamp,
  TicketStub,
  useToast,
} from '@/components/ui'
import { PageHeader } from '@/components/layout'
import { MarketPicker } from '@/components/bet/MarketPicker'
import { BetSlip } from '@/components/bet/BetSlip'
import { cn } from '@/lib/cn'
import { formatMatchDateTime } from '@/lib/datetime'
import { apiErrorMessage } from '@/api/client'
import { useMatch } from '@/api/matches'
import { usePlayers } from '@/api/players'
import {
  useDeleteTicket,
  useMyTickets,
  usePointsSettings,
  useSaveTicket,
} from '@/api/tickets'
import { useAuth } from '@/auth/AuthContext'
import type { MarketCode, MatchDetail, SelectionInput, Ticket } from '@/api/types'
import { describeSelection, pointsFor } from '@/lib/markets'
import { ticketCode, ticketVerdict } from '@/lib/ticket'
import { celebrateTicketOnce } from '@/lib/confetti'

type SelMap = Partial<Record<MarketCode, SelectionInput>>

export function Meci() {
  const { id } = useParams<{ id: string }>()
  const matchId = Number(id)
  const toast = useToast()
  const { user } = useAuth()

  const { data: match, isLoading, isError } = useMatch(matchId)
  const { data: players = [] } = usePlayers()
  const { data: points } = usePointsSettings()
  const { data: myTickets } = useMyTickets()

  const saveTicket = useSaveTicket()
  const deleteTicket = useDeleteTicket()

  const existingTicket = useMemo(
    () => myTickets?.find((t) => t.match_id === matchId) ?? null,
    [myTickets, matchId],
  )

  const [sel, setSel] = useState<SelMap>({})
  const [expired, setExpired] = useState(false)
  const [hydrated, setHydrated] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)

  // Pre-populează din biletul existent (o singură dată, când sosesc datele).
  useEffect(() => {
    if (hydrated || !myTickets) return
    if (existingTicket) {
      const next: SelMap = {}
      for (const s of existingTicket.selections) {
        next[s.market] = {
          market: s.market,
          pick: s.pick,
          line: s.line ?? undefined,
          player_id: s.player_id ?? undefined,
        }
      }
      setSel(next)
    }
    setHydrated(true)
  }, [myTickets, existingTicket, hydrated])

  const playerNames = useMemo(
    () => Object.fromEntries(players.map((p) => [p.id, p.name])),
    [players],
  )

  const selections = useMemo(
    () => Object.values(sel).filter((s): s is SelectionInput => !!s),
    [sel],
  )

  const locked = !match?.is_bettable || expired || match?.is_settled

  const toggle = (candidate: SelectionInput) => {
    if (locked) return
    setSel((prev) => {
      const cur = prev[candidate.market]
      const same =
        cur &&
        cur.pick === candidate.pick &&
        (cur.line ?? null) === (candidate.line ?? null) &&
        (cur.player_id ?? null) === (candidate.player_id ?? null)
      const next = { ...prev }
      if (same) delete next[candidate.market]
      else next[candidate.market] = candidate
      return next
    })
  }

  const save = async () => {
    if (selections.length === 0) return
    try {
      await saveTicket.mutateAsync({ matchId, selections })
      toast.success(
        existingTicket
          ? 'Bilet actualizat. Mai schimbi de câte ori vrei, până la start.'
          : 'Biletul e băgat. Baftă!',
      )
      setSheetOpen(false)
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  const remove = async () => {
    if (!existingTicket) return
    try {
      await deleteTicket.mutateAsync(existingTicket.id)
      setSel({})
      setSheetOpen(false)
      toast.success('Gata, s-a dus biletul.')
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-64 w-full" rounded="2xl" />
      </div>
    )
  }

  if (isError || !match) {
    return (
      <EmptyState
        icon={Lock}
        title="Meciul ăsta nu există"
        line="Poate a fost șters. Înapoi la meciuri."
        action={
          <Link to="/meciuri" className="font-semibold text-fortuna hover:underline">
            Vezi meciurile
          </Link>
        }
      />
    )
  }

  const total = selections.reduce((s, x) => s + pointsFor(x, points), 0)

  return (
    <>
      <Link
        to="/meciuri"
        className="mb-4 inline-flex items-center gap-1 text-sm text-white/50 hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" /> Toate meciurile
      </Link>

      {match.phase === 'GROUP' && (
        <div className="mb-3">
          <Badge tone="info">{`Grupa ${match.group_name ?? '?'} · etapa ${match.round_no}`}</Badge>
        </div>
      )}

      <PageHeader
        title={`${match.home_team?.name ?? 'TBD'} — ${match.away_team?.name ?? 'TBD'}`}
        subtitle={
          match.scheduled_at
            ? `${match.stage_label ?? ''} · ${formatMatchDateTime(match.scheduled_at)}`
            : (match.stage_label ?? 'Meci')
        }
        action={
          match.is_settled ? (
            <Badge tone="neutral">Încheiat</Badge>
          ) : match.scheduled_at ? (
            <Countdown target={match.scheduled_at} onExpire={() => setExpired(true)} />
          ) : (
            <Badge tone="neutral">Neprogramat</Badge>
          )
        }
      />

      {match.is_settled ? (
        <SettledView match={match} ticket={existingTicket} playerNames={playerNames} />
      ) : locked ? (
        <div className="rounded-2xl border border-white/10 bg-navy-900 p-6 text-center">
          <Lock className="mx-auto h-8 w-8 text-white/30" />
          <p className="mt-3 font-display text-lg text-white">Meciul a început.</p>
          <p className="mt-1 text-sm text-white/50">
            {existingTicket
              ? 'Biletul e bătut în cuie. Aștepți rezultatul.'
              : 'Prea târziu, campionule. Meciul a început.'}
          </p>
          {existingTicket && (
            <ul className="mx-auto mt-4 max-w-sm space-y-1 text-left text-sm text-white/70">
              {existingTicket.selections.map((s, i) => (
                <li key={i} className="flex justify-between">
                  <span>
                    {describeSelection(s, {
                      homeName: match.home_team?.name,
                      awayName: match.away_team?.name,
                      playerNames,
                    })}
                  </span>
                  <span className="font-mono text-white/50">+{s.points}p</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : !user ? (
        <EmptyState
          icon={Lock}
          title="Intră ca să pariezi"
          line="Îți faci cont într-un minut."
          action={
            <Link to="/login" className="font-semibold text-fortuna hover:underline">
              Intră în cont
            </Link>
          }
        />
      ) : (
        <>
          <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
            <MarketPicker
              match={match}
              players={players}
              points={points}
              value={sel}
              onToggle={toggle}
              disabled={locked}
            />
            {/* Desktop: biletul sticky lateral. Mobil: în bottom-sheet. */}
            <div className="hidden lg:sticky lg:top-24 lg:block lg:self-start">
              <BetSlip
                match={match}
                selections={selections}
                points={points}
                playerNames={playerNames}
                existingTicketId={existingTicket?.id ?? null}
                disabled={locked}
                saving={saveTicket.isPending}
                deleting={deleteTicket.isPending}
                onSave={save}
                onDelete={remove}
              />
            </div>
          </div>

          {/* Mobil: bară sticky + bottom-sheet cu biletul */}
          {selections.length > 0 && (
            <div className="fixed inset-x-0 bottom-0 z-betslip border-t border-white/10 bg-navy-950/95 p-3 pb-tabbar backdrop-blur lg:hidden">
              <div className="container-app flex items-center justify-between gap-3">
                <span className="text-sm text-white/70">
                  {selections.length} {selections.length === 1 ? 'selecție' : 'selecții'} ·{' '}
                  <span className="font-mono text-fortuna">{total}p</span>
                </span>
                <button
                  type="button"
                  onClick={() => setSheetOpen(true)}
                  className="inline-flex min-h-11 items-center rounded-xl bg-fortuna px-5 text-sm font-semibold text-ink shadow-glow active:scale-[.98]"
                >
                  Vezi biletul
                </button>
              </div>
            </div>
          )}

          <BottomSheet open={sheetOpen} onClose={() => setSheetOpen(false)} title="Biletul tău">
            <BetSlip
              match={match}
              selections={selections}
              points={points}
              playerNames={playerNames}
              existingTicketId={existingTicket?.id ?? null}
              disabled={locked}
              saving={saveTicket.isPending}
              deleting={deleteTicket.isPending}
              onSave={save}
              onDelete={remove}
            />
          </BottomSheet>
        </>
      )}
    </>
  )
}

function SettledView({
  match,
  ticket,
  playerNames,
}: {
  match: MatchDetail
  ticket: Ticket | null
  playerNames: Record<number, string>
}) {
  const verdict = ticket ? ticketVerdict(ticket) : null

  useEffect(() => {
    if (ticket && (ticket.total_points ?? 0) > 0) celebrateTicketOnce(ticket.id)
  }, [ticket])

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-white/10 bg-navy-900 p-6 text-center shadow-card">
        <p className="text-xs uppercase tracking-wider text-white/45">Scor final</p>
        <p className="mt-2 font-mono text-4xl font-bold tabular-nums text-white">
          {match.home_score} <span className="text-white/30">–</span> {match.away_score}
        </p>
        {match.penalties_home != null && (
          <p className="mt-1 text-xs text-white/45">
            după penalty-uri {match.penalties_home}–{match.penalties_away}
          </p>
        )}
        {match.scorers.length > 0 && (
          <p className="mt-2 text-sm text-white/60">
            Au marcat: {match.scorers.map((s) => s.name).join(', ')}
          </p>
        )}
      </div>

      {ticket ? (
        <TicketStub overlay={verdict ? <Stamp verdict={verdict} /> : undefined}>
          <div className="flex items-center justify-between border-b border-dashed border-ink/20 px-4 py-3">
            <span className="font-display text-sm">
              FEG<span className="text-bet">BET</span> · {ticketCode(ticket.id)}
            </span>
            <span className="font-mono text-sm font-semibold tabular-nums text-ink/70">
              {ticket.total_points ?? 0}p
            </span>
          </div>
          <ul className="divide-y divide-ink/10 px-4">
            {ticket.selections.map((s, i) => (
              <li key={i} className="flex items-center justify-between gap-3 py-2 text-sm">
                <span
                  className={cn(
                    s.is_correct === true && 'font-medium text-emerald-700',
                    s.is_correct === false && 'text-ink/40 line-through',
                  )}
                >
                  {describeSelection(s, {
                    homeName: match.home_team?.name,
                    awayName: match.away_team?.name,
                    playerNames,
                  })}
                </span>
                <span className="shrink-0 font-mono text-ink/70">
                  {s.is_correct ? `+${s.points_awarded}p` : '0p'}
                </span>
              </li>
            ))}
          </ul>
          <div className="flex items-center justify-between border-t border-dashed border-ink/20 px-4 py-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-ink/60">Total</span>
            <span className="font-mono text-lg font-bold tabular-nums">{ticket.total_points ?? 0}p</span>
          </div>
        </TicketStub>
      ) : (
        <p className="rounded-2xl border border-dashed border-white/10 p-6 text-center text-white/50">
          N-ai pariat pe meciul ăsta. Fotbalul e imprevizibil. Tu, mai puțin.
        </p>
      )}
    </div>
  )
}
