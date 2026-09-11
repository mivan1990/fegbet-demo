import { Chip } from '@/components/ui'
import type { TeamRef } from '@/api/types'

interface QualifyPickerProps {
  teams: TeamRef[]
  qualifiersCount: number
  /** Id-urile echipelor alese. Ordinea nu contează — e un set, nu un clasament. */
  value: number[]
  onChange: (ids: number[]) => void
  disabled?: boolean
}

/** Selectorul „ce echipe merg mai departe" dintr-o grupă — exact `qualifiersCount` alegeri. */
export function QualifyPicker({
  teams,
  qualifiersCount,
  value,
  onChange,
  disabled = false,
}: QualifyPickerProps) {
  const full = value.length >= qualifiersCount

  const toggle = (id: number) => {
    if (disabled) return
    if (value.includes(id)) {
      onChange(value.filter((x) => x !== id))
    } else if (!full) {
      onChange([...value, id])
    }
  }

  return (
    <div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {teams.map((t) => {
          const selected = value.includes(t.id)
          return (
            <Chip
              key={t.id}
              label={t.name}
              selected={selected}
              disabled={disabled || (!selected && full)}
              onClick={() => toggle(t.id)}
            />
          )
        })}
      </div>
      <p className="mt-2 text-xs text-white/45">
        {value.length}/{qualifiersCount} echipe alese
      </p>
    </div>
  )
}
