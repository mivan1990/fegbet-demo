import { useMemo, useState } from 'react'
import { GitBranch } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { EmptyState, Skeleton } from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatMatchDateTime } from '@/lib/datetime'
import { useBracket } from '@/api/matches'
import type { BracketRound, Match } from '@/api/types'

function teamInvolvesFeg(m: Match): boolean {
  return !!m.home_team?.is_feg || !!m.away_team?.is_feg
}

function TeamLine({
  team,
  score,
  won,
  settled,
}: {
  team: Match['home_team']
  score: number | null
  won: boolean
  settled: boolean
}) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-2 px-3 py-1.5 text-sm',
        won && 'font-semibold',
      )}
    >
      <span className="flex min-w-0 items-center gap-1.5">
        {team?.is_feg && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-feg-400" aria-hidden />}
        <span
          className={cn(
            'truncate',
            !team && 'text-white/30',
            team && won && 'text-fortuna',
            team && !won && 'text-white/80',
          )}
        >
          {team?.name ?? 'TBD'}
        </span>
      </span>
      {settled && (
        <span className={cn('shrink-0 font-mono tabular-nums', won ? 'text-fortuna' : 'text-white/50')}>
          {score ?? 0}
        </span>
      )}
    </div>
  )
}

function BracketCell({
  match,
  dim,
  showStage = true,
}: {
  match: Match
  dim?: boolean
  showStage?: boolean
}) {
  const settled = match.is_settled
  const homeWon = settled && match.winner_team_id != null && match.winner_team_id === match.home_team?.id
  const awayWon = settled && match.winner_team_id != null && match.winner_team_id === match.away_team?.id

  return (
    <div
      className={cn(
        'w-full overflow-hidden rounded-xl border bg-navy-900',
        settled ? 'border-fortuna/40' : 'border-white/10',
        dim && 'opacity-40',
      )}
    >
      {(showStage || match.scheduled_at) && (
        <div className="flex items-center justify-between gap-2 border-b border-white/5 px-3 py-1 text-[11px] uppercase tracking-wider text-white/35">
          <span className="truncate">
            {showStage ? (match.stage_label ?? `Runda ${match.round_no}`) : ''}
          </span>
          {match.scheduled_at && (
            <span className="shrink-0 normal-case tracking-normal">
              {formatMatchDateTime(match.scheduled_at)}
            </span>
          )}
        </div>
      )}
      <TeamLine team={match.home_team} score={match.home_score} won={homeWon} settled={settled} />
      <div className="h-px bg-white/5" />
      <TeamLine team={match.away_team} score={match.away_score} won={awayWon} settled={settled} />
      {settled && match.penalties_home != null && (
        <div className="border-t border-white/5 px-3 py-1 text-[11px] text-white/40">
          Penalty-uri {match.penalties_home}–{match.penalties_away}
        </div>
      )}
    </div>
  )
}

/** Coloana de conectori „]" intre doua runde. Cate un cot per meci din runda urmatoare. */
function Connectors({ prev, next }: { prev: BracketRound; next: BracketRound }) {
  return (
    <div className="flex w-10 shrink-0 flex-col justify-around pt-7" aria-hidden>
      {next.matches.map((m, i) => {
        const feeders = [prev.matches[i * 2], prev.matches[i * 2 + 1]].filter(Boolean)
        const onWinnerPath = feeders.some((f) => f?.is_settled)
        return (
          <div key={m.id} className="flex items-center">
            <div
              className={cn(
                'h-24 w-1/2 rounded-r-xl border-y border-r',
                onWinnerPath ? 'border-fortuna/70' : 'border-white/15',
              )}
            />
            <div
              className={cn(
                'h-px w-1/2 border-t',
                onWinnerPath ? 'border-fortuna/70' : 'border-white/15',
              )}
            />
          </div>
        )
      })}
    </div>
  )
}

/** Arbore desenat — vizibil de la `md:` in sus, cu scroll orizontal. */
function BracketTree({ rounds, fegOnly }: { rounds: BracketRound[]; fegOnly: boolean }) {
  return (
    <div className="scroll-x hidden rounded-2xl border border-white/10 bg-navy-950/40 p-4 md:block">
      <div className="flex min-w-max items-stretch">
        {rounds.map((round, idx) => (
          <div key={round.round_no} className="flex items-stretch">
            <div
              className="flex flex-col justify-around gap-6"
              style={{ minWidth: '14rem' }}
            >
              <p className="text-center text-xs font-semibold uppercase tracking-wider text-white/40">
                {round.stage_label ?? `Runda ${round.round_no}`}
              </p>
              {round.matches.map((m) => (
                <BracketCell
                  key={m.id}
                  match={m}
                  showStage={false}
                  dim={fegOnly && !teamInvolvesFeg(m)}
                />
              ))}
            </div>
            {idx < rounds.length - 1 && (
              <Connectors prev={round} next={rounds[idx + 1]} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export function Bracket() {
  const { data, isLoading, isError } = useBracket()
  const [activeRound, setActiveRound] = useState<number | null>(null)
  const [fegOnly, setFegOnly] = useState(false)

  const rounds = useMemo(() => data ?? [], [data])
  const current = activeRound ?? rounds[0]?.round_no ?? 1
  const currentRound = rounds.find((r) => r.round_no === current) ?? rounds[0]

  const mobileMatches = useMemo(() => {
    const list = currentRound?.matches ?? []
    return fegOnly ? list.filter(teamInvolvesFeg) : list
  }, [currentRound, fegOnly])

  if (isLoading) {
    return (
      <>
        <PageHeader title="Bracket" subtitle="Arborele turneului. Câștigătorul avansează." />
        <Skeleton className="h-96 w-full" rounded="2xl" />
      </>
    )
  }

  if (isError || rounds.length === 0) {
    return (
      <>
        <PageHeader title="Bracket" subtitle="Arborele turneului. Câștigătorul avansează." />
        <EmptyState
          icon={GitBranch}
          title="Fără bracket"
          line="Bracket-ul se stabilește după grupe — revino după ce se termină faza grupelor."
        />
      </>
    )
  }

  return (
    <>
      <PageHeader title="Bracket" subtitle="Arborele turneului. Câștigătorul avansează." />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setFegOnly((v) => !v)}
          aria-pressed={fegOnly}
          className={cn(
            'rounded-full border px-4 py-2 text-sm font-medium transition duration-150',
            fegOnly
              ? 'border-feg bg-feg/15 text-feg-400'
              : 'border-white/10 text-white/60 hover:text-white',
          )}
        >
          Traseul FEG
        </button>
      </div>

      {/* -------- Mobil: tab-uri de rundă + listă verticală -------- */}
      <div className="md:hidden">
        <div className="scroll-x -mx-4 mb-4 flex gap-2 px-4">
          {rounds.map((r) => (
            <button
              key={r.round_no}
              type="button"
              onClick={() => setActiveRound(r.round_no)}
              className={cn(
                'shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition duration-150',
                r.round_no === current
                  ? 'border-fortuna bg-fortuna text-ink'
                  : 'border-white/10 text-white/60 hover:text-white',
              )}
            >
              {r.stage_label ?? `Runda ${r.round_no}`}
            </button>
          ))}
        </div>

        {mobileMatches.length === 0 ? (
          <EmptyState
            icon={GitBranch}
            title="Nimic aici"
            line={fegOnly ? 'FEG nu joacă în runda asta.' : 'Runda n-are meciuri.'}
          />
        ) : (
          <div className="space-y-3">
            {mobileMatches.map((m) => (
              <BracketCell key={m.id} match={m} />
            ))}
          </div>
        )}
      </div>

      {/* -------- Desktop: arborele desenat -------- */}
      <BracketTree rounds={rounds} fegOnly={fegOnly} />
    </>
  )
}
