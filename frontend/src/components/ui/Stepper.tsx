import { Minus, Plus } from 'lucide-react'
import { cn } from '@/lib/cn'

interface StepperProps {
  label: string
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  className?: string
}

/** Contor −/+ cu câmp numeric. Folosit la scor / penalty-uri / goluri marcator. */
export function Stepper({ label, value, onChange, min = 0, max = 99, className }: StepperProps) {
  const clamp = (n: number) => Math.max(min, Math.min(max, n))
  return (
    <div className={cn('flex items-center justify-between gap-3', className)}>
      <span className="text-sm font-medium text-white/80">{label}</span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label={`Scade ${label}`}
          onClick={() => onChange(clamp(value - 1))}
          disabled={value <= min}
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/15 bg-navy-800 text-white hover:border-white/30 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna"
        >
          <Minus className="h-4 w-4" />
        </button>
        <input
          type="number"
          inputMode="numeric"
          aria-label={label}
          value={value}
          min={min}
          max={max}
          onChange={(e) => onChange(clamp(Number(e.target.value) || 0))}
          className="h-11 w-14 rounded-xl border border-white/10 bg-navy-800 text-center text-base font-mono tabular-nums text-white focus:border-white/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-fortuna"
        />
        <button
          type="button"
          aria-label={`Crește ${label}`}
          onClick={() => onChange(clamp(value + 1))}
          disabled={value >= max}
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/15 bg-navy-800 text-white hover:border-white/30 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
