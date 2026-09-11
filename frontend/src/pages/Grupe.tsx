import { useState } from 'react'
import { Users2 } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { EmptyState, Skeleton } from '@/components/ui'
import { GroupCard } from '@/components/group/GroupCard'
import { cn } from '@/lib/cn'
import { useGroups } from '@/api/groups'

export function Grupe() {
  const { data, isLoading, isError } = useGroups()
  const groups = data ?? []
  const [activeId, setActiveId] = useState<number | null>(null)

  const active = groups.find((g) => g.id === activeId) ?? groups[0] ?? null

  if (isLoading) {
    return (
      <>
        <PageHeader title="Grupe" subtitle="Clasamentul fiecărei grupe și cine crezi tu că merge mai departe." />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-96 w-full" rounded="2xl" />
          <Skeleton className="h-96 w-full" rounded="2xl" />
        </div>
      </>
    )
  }

  if (isError || groups.length === 0) {
    return (
      <>
        <PageHeader title="Grupe" subtitle="Clasamentul fiecărei grupe și cine crezi tu că merge mai departe." />
        <EmptyState
          icon={Users2}
          title="Grupele nu sunt gata"
          line="Adminul n-a tras încă la sorți grupele. Revino mai târziu."
        />
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Grupe"
        subtitle="Clasamentul fiecărei grupe și cine crezi tu că merge mai departe."
      />

      {/* -------- Mobil: tab-uri de grupă + un card -------- */}
      <div className="md:hidden">
        <div className="scroll-x -mx-4 mb-4 flex gap-2 px-4">
          {groups.map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => setActiveId(g.id)}
              className={cn(
                'shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition duration-150',
                g.id === active?.id
                  ? 'border-fortuna bg-fortuna text-ink'
                  : 'border-white/10 text-white/60 hover:text-white',
              )}
            >
              Grupa {g.name}
            </button>
          ))}
        </div>
        {active && <GroupCard group={active} />}
      </div>

      {/* -------- Desktop: grilă 2×2 -------- */}
      <div className="hidden gap-4 md:grid md:grid-cols-2">
        {groups.map((g) => (
          <GroupCard key={g.id} group={g} />
        ))}
      </div>
    </>
  )
}
