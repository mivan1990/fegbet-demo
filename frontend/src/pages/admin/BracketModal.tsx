import { useMemo, useState } from 'react'
import { Button, Modal, useToast } from '@/components/ui'
import { cn } from '@/lib/cn'
import { apiErrorMessage } from '@/api/client'
import { useTeams } from '@/api/teams'
import { useGenerateBracket } from '@/api/matches'

const SIZES = [4, 8, 16] as const

export function BracketModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const toast = useToast()
  const { data: teams } = useTeams()
  const generate = useGenerateBracket()

  const [size, setSize] = useState<(typeof SIZES)[number]>(8)
  const [picked, setPicked] = useState<number[]>([])

  const activeTeams = useMemo(() => (teams ?? []).filter((t) => t.is_active), [teams])

  const toggle = (id: number) => {
    setPicked((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= size) return prev
      return [...prev, id]
    })
  }

  const submit = async () => {
    if (picked.length !== size) return
    try {
      await generate.mutateAsync({ size, team_ids: picked })
      toast.success('Bracket generat.')
      setPicked([])
      onClose()
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Generează bracket"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Renunță
          </Button>
          <Button
            variant="primary"
            onClick={submit}
            loading={generate.isPending}
            disabled={picked.length !== size}
          >
            Generează ({picked.length}/{size})
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        <div>
          <p className="mb-2 text-sm font-medium text-white/80">Număr de echipe</p>
          <div className="flex gap-2">
            {SIZES.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setSize(s)
                  setPicked((p) => p.slice(0, s))
                }}
                className={cn(
                  'h-11 flex-1 rounded-xl border text-sm font-semibold transition duration-150',
                  size === s
                    ? 'border-fortuna bg-fortuna text-ink'
                    : 'border-white/10 bg-navy-800 text-white/70 hover:border-white/25',
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-white/80">
            Alege {size} echipe — ordinea contează (1 vs 2, 3 vs 4, …)
          </p>
          <p className="mb-3 text-xs text-white/45">
            Un bracket existent fără meciuri validate și fără bilete va fi înlocuit.
          </p>
          <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
            {activeTeams.map((team) => {
              const idx = picked.indexOf(team.id)
              const isPicked = idx !== -1
              return (
                <li key={team.id}>
                  <button
                    type="button"
                    onClick={() => toggle(team.id)}
                    className={cn(
                      'flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left text-sm transition duration-150',
                      isPicked
                        ? 'border-fortuna/60 bg-fortuna/10 text-white'
                        : 'border-white/10 bg-navy-800 text-white/70 hover:border-white/25',
                    )}
                  >
                    <span>{team.name}</span>
                    {isPicked && (
                      <span className="font-mono text-xs text-fortuna">#{idx + 1}</span>
                    )}
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
