import { Link } from 'react-router-dom'
import { ArrowRight, Crown, Trophy, Users2 } from 'lucide-react'
import { Button, Countdown, Skeleton } from '@/components/ui'
import { MatchCard } from '@/components/match/MatchCard'
import { cn } from '@/lib/cn'
import { useAuth } from '@/auth/AuthContext'
import { useMatches } from '@/api/matches'
import { useMyTickets } from '@/api/tickets'
import { useGroups } from '@/api/groups'
import { useLeaderboard } from '@/api/leaderboard'
import type { Match } from '@/api/types'

function nextThree(matches: Match[] | undefined): Match[] {
  return (matches ?? [])
    .filter((m) => !m.is_settled && m.scheduled_at)
    .sort((a, b) => (a.scheduled_at ?? '').localeCompare(b.scheduled_at ?? ''))
    .slice(0, 3)
}

function Hero({ isAuthed }: { isAuthed: boolean }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-navy-900 p-6 shadow-card md:p-10">
      <h1 className="font-display text-4xl leading-tight text-white md:text-5xl">
        Pariază pe orgoliu.
        <br />
        <span className="text-fortuna">Nu pe bani.</span>
      </h1>
      <p className="mt-4 max-w-xl text-white/60">
        Turneu eliminatoriu, echipa FEG în joc. Alegi selecțiile, bagi biletul, aduni puncte.
        Fără portofel, fără retrageri — doar clasamentul de la birou.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        {isAuthed ? (
          <Link to="/meciuri">
            <Button variant="primary" size="lg" iconRight={<ArrowRight className="h-4 w-4" />}>
              Vezi meciurile
            </Button>
          </Link>
        ) : (
          <>
            <Link to="/inregistrare">
              <Button variant="primary" size="lg" iconRight={<ArrowRight className="h-4 w-4" />}>
                Îmi fac cont
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="secondary" size="lg">
                Am deja cont
              </Button>
            </Link>
          </>
        )}
      </div>
    </section>
  )
}

function SectionTitle({ children, to, cta }: { children: string; to?: string; cta?: string }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <h2 className="font-display text-lg text-white">{children}</h2>
      {to && (
        <Link to={to} className="inline-flex items-center gap-1 text-sm text-fortuna hover:underline">
          {cta ?? 'Vezi tot'} <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      )}
    </div>
  )
}

function Top3({ className }: { className?: string }) {
  const { user } = useAuth()
  const { data, isLoading } = useLeaderboard()

  if (isLoading) return <Skeleton className={cn('h-40 w-full', className)} rounded="2xl" />
  if (!data || data.length === 0) return null

  return (
    <section className={className}>
      <SectionTitle to="/clasament" cta="Clasament complet">
        Top 3
      </SectionTitle>
      <ul className="divide-y divide-white/5 rounded-2xl border border-white/10 bg-navy-900">
        {data.slice(0, 3).map((row) => {
          const isMe = row.display_name === user?.display_name
          return (
            <li key={row.rank} className="flex items-center gap-3 px-4 py-3">
              <span
                className={cn(
                  'w-5 text-center font-mono text-sm tabular-nums',
                  row.rank === 1 ? 'text-fortuna' : 'text-white/40',
                )}
              >
                {row.rank}
              </span>
              {row.rank === 1 && <Crown className="h-4 w-4 shrink-0 text-fortuna" aria-hidden />}
              <span className={cn('min-w-0 flex-1 truncate', isMe ? 'text-fortuna' : 'text-white')}>
                {row.display_name}
              </span>
              <span className="shrink-0 font-mono text-sm font-semibold tabular-nums text-fortuna">
                {row.points}p
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function GroupsCta({ count }: { count: number }) {
  return (
    <section className="rounded-2xl border border-fortuna/40 bg-fortuna/10 p-6 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Users2 className="h-8 w-8 shrink-0 text-fortuna" aria-hidden />
          <div>
            <p className="font-display text-lg text-white">Ți-ai pus pronosticul pe grupe?</p>
            <p className="text-sm text-white/60">
              {count === 1
                ? 'O grupă încă așteaptă votul tău — cine merge mai departe?'
                : `${count} grupe încă așteaptă votul tău — cine merge mai departe?`}
            </p>
          </div>
        </div>
        <Link to="/grupe">
          <Button variant="primary" iconRight={<ArrowRight className="h-4 w-4" />}>
            Votează
          </Button>
        </Link>
      </div>
    </section>
  )
}

export function Home() {
  const { user } = useAuth()
  const { data: matches, isLoading: matchesLoading } = useMatches()
  const { data: tickets } = useMyTickets()
  const { data: groups } = useGroups()

  const upcoming = nextThree(matches)
  const openTickets = (tickets ?? []).filter((t) => t.status === 'OPEN')

  // Campioana, daca turneul chiar s-a incheiat: toate meciurile validate si
  // finala (runda cea mai mare din eliminatorii) are un castigator.
  const champion = (() => {
    const all = matches ?? []
    if (all.length === 0 || all.some((m) => !m.is_settled)) return null
    const knockout = all.filter((m) => m.phase === 'KNOCKOUT')
    if (knockout.length === 0) return null
    const final = knockout.reduce((a, b) => (b.round_no > a.round_no ? b : a))
    if (final.winner_team_id === null) return null
    const winner =
      final.home_team?.id === final.winner_team_id ? final.home_team : final.away_team
    return winner?.name ?? null
  })()
  const groupsWithoutPrediction = (groups ?? []).filter(
    (g) => !g.is_locked && g.my_prediction === null,
  )

  return (
    <div className="space-y-8">
      <Hero isAuthed={!!user} />

      {user && groupsWithoutPrediction.length > 0 && (
        <GroupsCta count={groupsWithoutPrediction.length} />
      )}

      <section>
        <SectionTitle to="/meciuri" cta="Toate meciurile">
          Următoarele meciuri
        </SectionTitle>
        {matchesLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-40 w-full" rounded="2xl" />
            <Skeleton className="h-40 w-full" rounded="2xl" />
          </div>
        ) : upcoming.length === 0 ? (
          champion ? (
            // Turneul s-a terminat: fara asta, un vizitator ar citi „revino mai
            // tarziu" si ar crede ca aplicatia e neconfigurata, nu ca s-a incheiat.
            <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center">
              <p className="text-sm uppercase tracking-widest text-white/40">Turneul s-a încheiat</p>
              <p className="mt-2 text-2xl font-bold text-brand">{champion} a câștigat</p>
              <Link to="/bracket" className="mt-4 inline-block text-sm text-white/60 underline hover:text-white">
                Vezi drumul până la finală
              </Link>
            </div>
          ) : (
            <p className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-white/50">
              Niciun meci programat momentan. Revino după ce adminul pune orele.
            </p>
          )
        ) : (
          <div className="space-y-3">
            {upcoming.map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
          </div>
        )}
      </section>

      {user && openTickets.length > 0 && (
        <section>
          <SectionTitle to="/biletele-mele" cta="Toate biletele">
            Biletele tale deschise
          </SectionTitle>
          <ul className="space-y-2">
            {openTickets.map((t) => (
              <li key={t.id}>
                <Link
                  to={`/meci/${t.match_id}`}
                  className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-navy-900 px-4 py-3 hover:border-white/25"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-white">
                      {t.match?.home_name ?? 'TBD'} vs {t.match?.away_name ?? 'TBD'}
                    </span>
                    <span className="text-xs text-white/45">
                      {t.selections.length}{' '}
                      {t.selections.length === 1 ? 'selecție' : 'selecții'} · poți câștiga{' '}
                      <span className="font-mono text-fortuna">{t.potential_points}p</span>
                    </span>
                  </span>
                  {t.match?.scheduled_at && (
                    <Countdown target={t.match.scheduled_at} className="shrink-0" />
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {user && openTickets.length === 0 && upcoming.length > 0 && (
        <section className="rounded-2xl border border-white/10 bg-navy-900 p-6 text-center shadow-card">
          <Trophy className="mx-auto h-8 w-8 text-white/20" aria-hidden />
          <p className="mt-3 text-white/70">N-ai niciun bilet deschis. Curaj!</p>
          <Link to="/meciuri" className="mt-3 inline-block font-semibold text-fortuna hover:underline">
            Alege un meci
          </Link>
        </section>
      )}

      <Top3 />
    </div>
  )
}
