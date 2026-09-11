import { Badge } from '@/components/ui'
import { cn } from '@/lib/cn'
import type { StandingRow } from '@/api/types'

interface GroupStandingsProps {
  standings: StandingRow[]
  qualifiersCount: number
  className?: string
}

/**
 * Clasamentul unei grupe — mobile-first, cu scroll orizontal propriu (nu al paginii).
 * Primele `qualifiersCount` locuri au fundal verde discret + „→ sferturi";
 * echipele nedepartajabile primesc un `Badge` „egale" (PLAN_GRUPE.md 7.2).
 */
export function GroupStandings({ standings, qualifiersCount, className }: GroupStandingsProps) {
  if (standings.length === 0) {
    return (
      <p className={cn('rounded-xl border border-dashed border-white/10 p-4 text-center text-sm text-white/45', className)}>
        Grupa n-are încă echipe.
      </p>
    )
  }

  return (
    <div className={cn('scroll-x rounded-xl border border-white/10', className)}>
      <table className="w-full min-w-[440px] text-sm">
        <thead>
          <tr className="border-b border-white/10 text-left text-[11px] uppercase tracking-wider text-white/40">
            <th className="px-2 py-2 text-center font-medium">#</th>
            <th className="px-2 py-2 font-medium">Echipă</th>
            <th className="px-2 py-2 text-center font-medium">J</th>
            <th className="px-2 py-2 text-center font-medium">V</th>
            <th className="px-2 py-2 text-center font-medium">E</th>
            <th className="px-2 py-2 text-center font-medium">Î</th>
            <th className="px-2 py-2 text-center font-medium">GM:GP</th>
            <th className="px-2 py-2 text-center font-medium">+/-</th>
            <th className="px-2 py-2 text-center font-medium">P</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((row) => {
            const qualifies = row.rank <= qualifiersCount
            const tied = row.tied_with.length > 0
            return (
              <tr
                key={row.team_id}
                className={cn('border-b border-white/5 last:border-0', qualifies && 'bg-emerald-500/10')}
              >
                <td className="px-2 py-2 text-center font-mono tabular-nums text-white/60">{row.rank}</td>
                <td className="px-2 py-2">
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span className={cn('truncate', qualifies ? 'font-semibold text-white' : 'text-white/85')}>
                      {row.team.name}
                    </span>
                    {qualifies && (
                      <span className="shrink-0 text-[11px] font-semibold uppercase tracking-wide text-emerald-300">
                        → sferturi
                      </span>
                    )}
                    {tied && <Badge tone="urgent">egale</Badge>}
                  </span>
                </td>
                <td className="px-2 py-2 text-center font-mono tabular-nums text-white/70">{row.played}</td>
                <td className="px-2 py-2 text-center font-mono tabular-nums text-white/70">{row.won}</td>
                <td className="px-2 py-2 text-center font-mono tabular-nums text-white/70">{row.drawn}</td>
                <td className="px-2 py-2 text-center font-mono tabular-nums text-white/70">{row.lost}</td>
                <td className="px-2 py-2 text-center font-mono tabular-nums text-white/70">
                  {row.goals_for}:{row.goals_against}
                </td>
                <td className="px-2 py-2 text-center font-mono tabular-nums text-white/70">
                  {row.goal_diff > 0 ? `+${row.goal_diff}` : row.goal_diff}
                </td>
                <td className="px-2 py-2 text-center font-mono text-base font-bold tabular-nums text-fortuna">
                  {row.points}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
