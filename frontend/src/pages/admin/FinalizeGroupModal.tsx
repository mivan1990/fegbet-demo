import { useEffect, useState } from 'react'
import { Button, Modal, useToast } from '@/components/ui'
import { cn } from '@/lib/cn'
import { apiErrorMessage } from '@/api/client'
import { useFinalizeGroup } from '@/api/groups'
import type { Group } from '@/api/types'

interface Props {
  group: Group | null
  onClose: () => void
}

/**
 * Backend-ul raportează departajarea ambiguă cu ID-uri de echipă („echipa 12"), nu cu
 * nume — mapăm la nume din `group.standings` ca adminul să înțeleagă mesajul.
 */
function humanizeGroupError(message: string, group: Group): string {
  const byId = new Map(group.standings.map((s) => [s.team_id, s.team.name]))
  return message.replace(/echipa (\d+)/gi, (match, idStr: string) => byId.get(Number(idStr)) ?? match)
}

export function FinalizeGroupModal({ group, onClose }: Props) {
  const toast = useToast()
  const finalize = useFinalizeGroup()
  const [manual, setManual] = useState(false)
  const [picked, setPicked] = useState<number[]>([])

  useEffect(() => {
    setManual(false)
    setPicked([])
  }, [group?.id])

  const qualifiersCount = group?.qualifiers_count ?? 0
  const unsettled = group ? group.matches.filter((m) => !m.is_settled).length : 0

  const toggle = (teamId: number) => {
    setPicked((prev) => {
      if (prev.includes(teamId)) return prev.filter((id) => id !== teamId)
      if (prev.length >= qualifiersCount) return prev
      return [...prev, teamId]
    })
  }

  const submit = async () => {
    if (!group) return
    try {
      await finalize.mutateAsync({ id: group.id, teamIds: manual ? picked : undefined })
      toast.success(`Grupa ${group.name} a fost finalizată.`)
      onClose()
    } catch (err) {
      const raw = apiErrorMessage(err)
      toast.error(humanizeGroupError(raw, group))
    }
  }

  return (
    <Modal
      open={group !== null}
      onClose={onClose}
      title={group ? `Finalizează grupa ${group.name}` : 'Finalizează grupa'}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Renunță
          </Button>
          <Button
            variant="primary"
            onClick={submit}
            loading={finalize.isPending}
            disabled={!group || unsettled > 0 || (manual && picked.length !== qualifiersCount)}
          >
            Finalizează
          </Button>
        </>
      }
    >
      {group && (
        <div className="space-y-4">
          {unsettled > 0 ? (
            <p className="rounded-xl border border-bet/40 bg-bet/10 p-3 text-sm text-white/80">
              Mai sunt {unsettled} meciuri nevalidate în grupa {group.name}. Validează-le întâi.
            </p>
          ) : (
            <p className="text-sm text-white/60">
              Se califică primele {qualifiersCount} din clasament. Dacă departajarea e ambiguă,
              alege manual echipele calificate.
            </p>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setManual(false)}
              className={cn(
                'h-10 flex-1 rounded-xl border text-sm font-semibold transition duration-150',
                !manual
                  ? 'border-fortuna bg-fortuna text-ink'
                  : 'border-white/10 bg-navy-800 text-white/70 hover:border-white/25',
              )}
            >
              Automat
            </button>
            <button
              type="button"
              onClick={() => setManual(true)}
              className={cn(
                'h-10 flex-1 rounded-xl border text-sm font-semibold transition duration-150',
                manual
                  ? 'border-fortuna bg-fortuna text-ink'
                  : 'border-white/10 bg-navy-800 text-white/70 hover:border-white/25',
              )}
            >
              Aleg eu echipele
            </button>
          </div>

          {manual && (
            <div>
              <p className="mb-2 text-sm text-white/70">
                Alege {qualifiersCount} echipe calificate ({picked.length}/{qualifiersCount})
              </p>
              <ul className="space-y-2">
                {[...group.standings]
                  .sort((a, b) => a.rank - b.rank)
                  .map((row) => {
                    const isPicked = picked.includes(row.team_id)
                    return (
                      <li key={row.team_id}>
                        <button
                          type="button"
                          onClick={() => toggle(row.team_id)}
                          disabled={!isPicked && picked.length >= qualifiersCount}
                          className={cn(
                            'flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left text-sm transition duration-150',
                            isPicked
                              ? 'border-fortuna/60 bg-fortuna/10 text-white'
                              : 'border-white/10 bg-navy-800 text-white/70 hover:border-white/25',
                          )}
                        >
                          <span>
                            #{row.rank} {row.team.name}
                          </span>
                          <span className="font-mono text-xs text-white/50">{row.points}p</span>
                        </button>
                      </li>
                    )
                  })}
              </ul>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
