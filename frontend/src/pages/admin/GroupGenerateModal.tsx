import { useMemo, useState } from 'react'
import { Button, Modal, useToast } from '@/components/ui'
import { cn } from '@/lib/cn'
import { apiErrorMessage } from '@/api/client'
import { useTeams } from '@/api/teams'
import { useGenerateGroups } from '@/api/groups'

type GroupName = 'A' | 'B' | 'C' | 'D'
const GROUP_NAMES: GroupName[] = ['A', 'B', 'C', 'D']

export function GroupGenerateModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const toast = useToast()
  const { data: teams } = useTeams()
  const generate = useGenerateGroups()

  const [activeGroup, setActiveGroup] = useState<GroupName>('A')
  const [groups, setGroups] = useState<Record<GroupName, number[]>>({ A: [], B: [], C: [], D: [] })

  const activeTeams = useMemo(() => (teams ?? []).filter((t) => t.is_active), [teams])

  const groupOf = (teamId: number): GroupName | null =>
    GROUP_NAMES.find((g) => groups[g].includes(teamId)) ?? null

  const toggle = (teamId: number) => {
    setGroups((prev) => {
      const current = prev[activeGroup]
      if (current.includes(teamId)) {
        return { ...prev, [activeGroup]: current.filter((id) => id !== teamId) }
      }
      if (current.length >= 4) return prev
      return { ...prev, [activeGroup]: [...current, teamId] }
    })
  }

  const readyGroups = GROUP_NAMES.filter((g) => groups[g].length === 4)

  const submit = async () => {
    if (readyGroups.length === 0) return
    try {
      await generate.mutateAsync(readyGroups.map((name) => ({ name, team_ids: groups[name] })))
      toast.success('Grupe generate.')
      setGroups({ A: [], B: [], C: [], D: [] })
      onClose()
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Generează grupe"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Renunță
          </Button>
          <Button
            variant="primary"
            onClick={submit}
            loading={generate.isPending}
            disabled={readyGroups.length === 0}
          >
            Generează ({readyGroups.length} {readyGroups.length === 1 ? 'grupă' : 'grupe'})
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        <p className="text-xs text-white/45">
          Alege câte 4 echipe pentru fiecare grupă. O grupă existentă cu meciuri de grupă
          validate sau pronosticuri plasate nu poate fi regenerată — serverul refuză.
        </p>

        <div className="flex gap-2">
          {GROUP_NAMES.map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => setActiveGroup(g)}
              className={cn(
                'h-11 flex-1 rounded-xl border text-sm font-semibold transition duration-150',
                activeGroup === g
                  ? 'border-fortuna bg-fortuna text-ink'
                  : 'border-white/10 bg-navy-800 text-white/70 hover:border-white/25',
              )}
            >
              {g} ({groups[g].length}/4)
            </button>
          ))}
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-white/80">
            Grupa {activeGroup} — alege 4 echipe
          </p>
          <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
            {activeTeams.map((team) => {
              const owner = groupOf(team.id)
              const inActive = owner === activeGroup
              const elsewhere = owner !== null && owner !== activeGroup
              return (
                <li key={team.id}>
                  <button
                    type="button"
                    disabled={elsewhere || (!inActive && groups[activeGroup].length >= 4)}
                    onClick={() => toggle(team.id)}
                    className={cn(
                      'flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left text-sm transition duration-150',
                      inActive
                        ? 'border-fortuna/60 bg-fortuna/10 text-white'
                        : 'border-white/10 bg-navy-800 text-white/70 hover:border-white/25',
                      elsewhere && 'opacity-40',
                    )}
                  >
                    <span>{team.name}</span>
                    {inActive && <span className="font-mono text-xs text-fortuna">Grupa {activeGroup}</span>}
                    {elsewhere && <span className="font-mono text-xs text-white/40">Grupa {owner}</span>}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </Modal>
  )
}
