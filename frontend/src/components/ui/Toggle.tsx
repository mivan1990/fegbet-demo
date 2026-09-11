import { useId } from 'react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
  hint?: ReactNode
  disabled?: boolean
}

/** Comutator on/off cu etichetă. Folosit în formularele de admin. */
export function Toggle({ checked, onChange, label, hint, disabled = false }: ToggleProps) {
  const id = useId()
  return (
    <div className="flex items-start justify-between gap-4">
      <label htmlFor={id} className="flex-1">
        <span className="block text-sm font-medium text-white/80">{label}</span>
        {hint && <span className="mt-1 block text-xs text-white/45">{hint}</span>}
      </label>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative h-6 w-11 shrink-0 rounded-full transition duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950',
          checked ? 'bg-fortuna' : 'bg-white/15',
          disabled && 'opacity-40 cursor-not-allowed',
        )}
      >
        <span
          className={cn(
            'absolute top-1 h-4 w-4 rounded-full bg-navy-950 transition duration-150',
            checked ? 'left-6' : 'left-1',
          )}
        />
      </button>
    </div>
  )
}
