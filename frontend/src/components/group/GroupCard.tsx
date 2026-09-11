import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Users } from 'lucide-react'
import { Badge, Button, Countdown, EmptyState, Stamp, TicketStub, useToast } from '@/components/ui'
import { MatchCard } from '@/components/match/MatchCard'
import { GroupStandings } from './GroupStandings'
import { QualifyPicker } from './QualifyPicker'
import { cn } from '@/lib/cn'
import { apiErrorMessage } from '@/api/client'
import { celebrateGroupPredictionOnce } from '@/lib/confetti'
import { groupPredictionVerdict, ticketCode } from '@/lib/ticket'
import { useDeleteGroupPrediction, useSaveGroupPrediction } from '@/api/groups'
import { usePointsSettings } from '@/api/tickets'
import { useAuth } from '@/auth/AuthContext'
import type { Group, Match } from '@/api/types'

function PredictionBlock({ group }: { group: Group }) {
  const { user } = useAuth()
  const toast = useToast()
  const save = useSaveGroupPrediction()
  const del = useDeleteGroupPrediction()
  const { data: points } = usePointsSettings()

  const pred = group.my_prediction
  const [picked, setPicked] = useState<number[]>(() => pred?.picks.map((p) => p.team_id) ?? [])

  // Re-hidratează selecția dacă pronosticul de pe server se schimbă (ex. după salvare).
  useEffect(() => {
    setPicked(pred?.picks.map((p) => p.team_id) ?? [])
  }, [pred])

  useEffect(() => {
    if (pred && pred.status === 'SETTLED' && (pred.total_points ?? 0) > 0) {
      celebrateGroupPredictionOnce(pred.id)
    }
  }, [pred])

  const qualifyPts = points?.['pts.group.qualify'] ?? 0
  const perfectPts = points?.['pts.group.perfect'] ?? 0
  const potential = group.qualifiers_count * qualifyPts + (perfectPts > 0 ? perfectPts : 0)

  if (!user) {
    return (
      <div className="rounded-xl border border-dashed border-white/10 p-4 text-center text-sm text-white/60">
        <Link to="/login" className="font-semibold text-fortuna hover:underline">
          Intră în cont
        </Link>{' '}
        ca să votezi cine merge mai departe din grupa {group.name}.
      </div>
    )
  }

  // Decontat -> stampila, aceeasi conventie ca la bilete.
  if (pred && pred.status === 'SETTLED') {
    const verdict = groupPredictionVerdict(pred)
    return (
      <TicketStub overlay={verdict ? <Stamp verdict={verdict} /> : undefined}>
        <div className="border-b border-dashed border-ink/20 px-4 py-3">
          <p className="font-display text-sm">
            FEG<span className="text-bet">BET</span> · {ticketCode(pred.id)}
          </p>
          <p className="text-xs text-ink/60">Grupa {group.name} · cine merge mai departe</p>
        </div>
        <ul className="divide-y divide-ink/10 px-4">
          {pred.picks.map((p) => (
            <li key={p.team_id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span
                className={cn(
                  p.is_correct === true && 'font-medium text-emerald-700',
                  p.is_correct === false && 'text-ink/40 line-through',
                )}
              >
                {p.team_name}
              </span>
              <span className="shrink-0 font-mono text-ink/70">
                {p.is_correct ? `+${p.points_awarded}p` : '0p'}
              </span>
            </li>
          ))}
        </ul>
        <div className="flex items-center justify-between border-t border-dashed border-ink/20 px-4 py-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-ink/60">Total</span>
          <span className="font-mono text-lg font-bold tabular-nums">{pred.total_points ?? 0}p</span>
        </div>
      </TicketStub>
    )
  }

  // Pronostic plasat, dar grupa a inceput deja -> read-only.
  if (pred && group.is_locked) {
    return (
      <div className="rounded-xl border border-white/10 bg-navy-800 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium text-white/80">Pronosticul tău</p>
          <Countdown target={group.locks_at} expiredLabel="Grupa a început" />
        </div>
        <ul className="flex flex-wrap gap-2">
          {pred.picks.map((p) => (
            <li
              key={p.team_id}
              className="rounded-full border border-white/15 bg-navy-900 px-3 py-1 text-sm text-white/85"
            >
              {p.team_name}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  // N-a apucat sa voteze inainte ca grupa sa se blocheze — textul vine din backend
  // (group.missed_prediction_reason), aceeasi sursa ca regula de blocare, ca sa nu
  // spuna "a început" despre o grupa care de fapt s-a ÎNCHEIAT (finalizata).
  if (!pred && group.is_locked) {
    return (
      <EmptyState
        icon={Users}
        title="Ai ratat fereastra de pronostic"
        line={
          group.missed_prediction_reason ??
          `Grupa ${group.name} a început deja — n-ai apucat să votezi cine merge mai departe.`
        }
        className="border-0 bg-navy-800 py-8"
      />
    )
  }

  // Grupa n-are inca meciuri programate -> nu se poate paria (PLAN_GRUPE.md 5.4).
  if (!pred && !group.locks_at) {
    return (
      <EmptyState
        icon={Users}
        title="Grupa n-are încă program"
        line="Revino după ce adminul pune orele meciurilor grupei."
        className="border-0 bg-navy-800 py-8"
      />
    )
  }

  const submit = async () => {
    if (picked.length !== group.qualifiers_count) return
    try {
      await save.mutateAsync({ groupId: group.id, predictionId: pred?.id ?? null, teamIds: picked })
      toast.success(pred ? 'Pronostic actualizat.' : 'Pronostic salvat. Baftă!')
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  const remove = async () => {
    if (!pred) return
    try {
      await del.mutateAsync(pred.id)
      toast.success('Pronostic șters.')
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  return (
    <div className="rounded-xl border border-white/10 bg-navy-800 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-white/80">
          Cine merge mai departe din grupa {group.name}?
        </p>
        {group.locks_at && <Countdown target={group.locks_at} />}
      </div>
      <QualifyPicker
        teams={group.teams}
        qualifiersCount={group.qualifiers_count}
        value={picked}
        onChange={setPicked}
      />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-white/45">
          Poți câștiga <span className="font-mono text-fortuna">{potential}p</span>
        </p>
        <div className="flex gap-2">
          {pred && (
            <Button variant="ghost" size="sm" loading={del.isPending} onClick={remove}>
              Șterge
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            disabled={picked.length !== group.qualifiers_count}
            loading={save.isPending}
            onClick={submit}
          >
            Salvează pronosticul
          </Button>
        </div>
      </div>
    </div>
  )
}

function groupStatusBadge(group: Group) {
  if (group.is_finalized) return <Badge tone="success">Finalizată</Badge>
  if (group.is_complete) return <Badge tone="info">Meciuri încheiate</Badge>
  if (group.is_locked) return <Badge tone="neutral">În desfășurare</Badge>
  return <Badge tone="neutral">Se califică primele {group.qualifiers_count}</Badge>
}

export function GroupCard({ group }: { group: Group }) {
  const matchesByRound = useMemo(() => {
    const map = new Map<number, Match[]>()
    for (const m of group.matches) {
      const arr = map.get(m.round_no) ?? []
      arr.push(m)
      map.set(m.round_no, arr)
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0])
  }, [group.matches])

  return (
    <div className="rounded-2xl border border-white/10 bg-navy-900 p-4 shadow-card md:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl text-white">Grupa {group.name}</h2>
        {groupStatusBadge(group)}
      </div>

      <div className="mb-5">
        <PredictionBlock group={group} />
      </div>

      <GroupStandings standings={group.standings} qualifiersCount={group.qualifiers_count} className="mb-5" />

      {group.is_finalized && group.qualified.length > 0 && (
        <p className="mb-5 text-sm text-white/60">
          Calificate: {group.qualified.map((t) => t.name).join(', ')}
        </p>
      )}

      {matchesByRound.length > 0 && (
        <div className="space-y-4">
          {matchesByRound.map(([roundNo, matches]) => (
            <section key={roundNo}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/40">
                Etapa {roundNo}
              </h3>
              <div className="space-y-2">
                {matches.map((m) => (
                  <MatchCard key={m.id} match={m} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
