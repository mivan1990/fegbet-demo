import { useMemo, useState } from 'react'
import { CalendarX } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { EmptyState, MatchCardSkeleton } from '@/components/ui'
import { MatchCard } from '@/components/match/MatchCard'
import { cn } from '@/lib/cn'
import { useMatches } from '@/api/matches'
import type { Match } from '@/api/types'

type Filter = 'toate' | 'deschise' | 'incepute' | 'validate'

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'toate', label: 'Toate' },
  { key: 'deschise', label: 'Deschise' },
  { key: 'incepute', label: 'Începute' },
  { key: 'validate', label: 'Validate' },
]

function matchesFilter(m: Match, f: Filter): boolean {
  if (f === 'toate') return true
  if (f === 'deschise') return m.is_bettable
  if (f === 'incepute') return m.is_locked && !m.is_settled
  return m.is_settled
}

export function Meciuri() {
  const { data, isLoading, isError } = useMatches()
  const [filter, setFilter] = useState<Filter>('toate')

  const filtered = useMemo(
    () => (data ?? []).filter((m) => matchesFilter(m, filter)),
    [data, filter],
  )

  return (
    <>
      <PageHeader title="Meciuri" subtitle="Toate meciurile turneului. Filtrează după ce te interesează." />

      <div className="scroll-x -mx-4 mb-6 flex gap-2 px-4 md:mx-0 md:px-0">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFilter(f.key)}
            className={cn(
              'shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition duration-150',
              filter === f.key
                ? 'border-fortuna bg-fortuna text-ink'
                : 'border-white/10 text-white/60 hover:text-white',
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <MatchCardSkeleton />
          <MatchCardSkeleton />
          <MatchCardSkeleton />
        </div>
      ) : isError ? (
        <EmptyState
          icon={CalendarX}
          title="Am pierdut mingea"
          line="Nu am putut încărca meciurile. Mai încearcă."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={CalendarX}
          title="Nimic aici"
          line={
            filter === 'toate'
              ? 'Turneul n-a început. Revino după ce adminul pune bracket-ul.'
              : 'Niciun meci în categoria asta deocamdată.'
          }
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </div>
      )}
    </>
  )
}
