import { useMemo, useState } from 'react'
import { RotateCcw, Save } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Button, Skeleton, Stepper, useToast } from '@/components/ui'
import { apiErrorMessage } from '@/api/client'
import { useAdminSettings, useUpdateSettings } from '@/api/admin'
import type { PointsMap } from '@/api/types'

interface Group {
  title: string
  hint?: string
  keys: { key: string; label: string }[]
}

const GROUPS: Group[] = [
  {
    title: 'Câștigător & calificare',
    keys: [
      { key: 'pts.winner.side', label: 'Câștigător (gazde / oaspeți)' },
      { key: 'pts.winner.draw', label: 'Câștigător — egal în timp regulamentar' },
      { key: 'pts.qualify', label: 'Echipa care se califică' },
    ],
  },
  {
    title: 'Total goluri — peste',
    hint: 'Cu cât linia e mai greu de atins, cu atât punctele sunt mai mari.',
    keys: [
      { key: 'pts.goals.over.0.5', label: 'Peste 0.5' },
      { key: 'pts.goals.over.1.5', label: 'Peste 1.5' },
      { key: 'pts.goals.over.2.5', label: 'Peste 2.5' },
      { key: 'pts.goals.over.3.5', label: 'Peste 3.5' },
    ],
  },
  {
    title: 'Total goluri — sub',
    keys: [
      { key: 'pts.goals.under.3.5', label: 'Sub 3.5' },
      { key: 'pts.goals.under.2.5', label: 'Sub 2.5' },
      { key: 'pts.goals.under.1.5', label: 'Sub 1.5' },
      { key: 'pts.goals.under.0.5', label: 'Sub 0.5' },
    ],
  },
  {
    title: 'Ambele echipe înscriu',
    keys: [
      { key: 'pts.btts.yes', label: 'Da' },
      { key: 'pts.btts.no', label: 'Nu' },
    ],
  },
  {
    title: 'Marcator & bonus',
    hint: 'Bonusul „bilet perfect" se acordă când toate selecțiile unui bilet sunt corecte.',
    keys: [
      { key: 'pts.scorer', label: 'Marcator FEG corect' },
      { key: 'pts.bonus.perfect', label: 'Bonus bilet perfect' },
    ],
  },
  {
    title: 'Pronosticul de grupă',
    hint: 'Punctele pentru „cine merge mai departe" votat la nivel de grupă (Faza 9).',
    keys: [
      { key: 'pts.group.qualify', label: 'Echipă ghicită corect în grupă' },
      { key: 'pts.group.perfect', label: 'Bonus — toate echipele din grupă ghicite (0 = dezactivat)' },
    ],
  },
]

function diff(current: PointsMap, base: PointsMap): PointsMap {
  const out: PointsMap = {}
  for (const [k, v] of Object.entries(current)) {
    if (base[k] !== v) out[k] = v
  }
  return out
}

export function AdminSettings() {
  const toast = useToast()
  const { data, isLoading } = useAdminSettings()
  const update = useUpdateSettings()
  const [draft, setDraft] = useState<PointsMap | null>(null)

  const base = data ?? {}
  const values = draft ?? base
  const changed = useMemo(() => diff(values, base), [values, base])
  const changedCount = Object.keys(changed).length

  const set = (key: string, value: number) =>
    setDraft({ ...(draft ?? base), [key]: value })

  const save = async () => {
    if (changedCount === 0) return
    try {
      await update.mutateAsync(changed)
      setDraft(null)
      toast.success(
        `Punctaje salvate. Se aplică la decontările următoare — biletele deja decontate rămân neschimbate.`,
      )
    } catch (err) {
      toast.error(apiErrorMessage(err))
    }
  }

  if (isLoading) {
    return (
      <>
        <PageHeader title="Setări" subtitle="Punctajele acordate pentru fiecare tip de selecție." />
        <div className="space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-40 w-full" rounded="2xl" />
          ))}
        </div>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Setări"
        subtitle="Punctajele acordate pentru fiecare tip de selecție."
        action={
          <div className="flex gap-2">
            {changedCount > 0 && (
              <Button
                variant="ghost"
                iconLeft={<RotateCcw className="h-4 w-4" />}
                onClick={() => setDraft(null)}
              >
                Anulează
              </Button>
            )}
            <Button
              variant="primary"
              iconLeft={<Save className="h-4 w-4" />}
              onClick={save}
              loading={update.isPending}
              disabled={changedCount === 0}
            >
              {changedCount > 0 ? `Salvează (${changedCount})` : 'Salvează'}
            </Button>
          </div>
        }
      />

      <div className="mb-6 rounded-xl border border-feg/30 bg-feg/5 px-4 py-3 text-sm text-white/70">
        Modificările afectează doar decontările <strong className="text-white">viitoare</strong>.
        Un bilet deja decontat se recalculează doar dacă adminul re-validează manual meciul.
      </div>

      <div className="space-y-4">
        {GROUPS.map((group) => (
          <section
            key={group.title}
            className="rounded-2xl border border-white/10 bg-navy-900 p-4 shadow-card md:p-6"
          >
            <h2 className="font-display text-lg text-white">{group.title}</h2>
            {group.hint && <p className="mt-1 text-xs text-white/45">{group.hint}</p>}
            <div className="mt-4 space-y-3">
              {group.keys.map(({ key, label }) => (
                <Stepper
                  key={key}
                  label={label}
                  value={values[key] ?? 0}
                  min={0}
                  max={50}
                  onChange={(v) => set(key, v)}
                  className={changed[key] !== undefined ? 'rounded-lg bg-fortuna/5 px-2' : ''}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </>
  )
}
