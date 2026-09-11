import { forwardRef } from 'react'
import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  selected?: boolean
  /** Punctele aduse de selectie, afisate mic pe randul de jos: "+3p". */
  points?: number
  label: string
  /** Detaliu optional pe primul rand (ex. linia la Total goluri). */
  hint?: string
}

/**
 * Cea mai folosita componenta din aplicatie: o optiune de pariere.
 * Un tap selecteaza, al doilea tap pe acelasi chip deselecteaza (gestionat de parinte).
 */
export const Chip = forwardRef<HTMLButtonElement, ChipProps>(function Chip(
  { selected = false, points, label, hint, className, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled}
      aria-pressed={selected}
      className={cn(
        'flex min-h-11 w-full flex-col items-center justify-center rounded-xl px-3 py-2',
        'text-center transition duration-150 ease-smooth',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna',
        'focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950',
        selected
          ? 'bg-fortuna text-ink border border-fortuna scale-[1.02]'
          : 'bg-navy-800 text-white border border-white/10 hover:border-white/25',
        disabled && 'opacity-35 pointer-events-none hover:border-white/10',
        className,
      )}
      {...rest}
    >
      <span className="text-sm font-semibold leading-tight">
        {label}
        {hint && <span className={cn('ml-1 font-normal', selected ? 'text-ink/70' : 'text-white/50')}>{hint}</span>}
      </span>
      {typeof points === 'number' && (
        <span
          className={cn(
            'mt-1 font-mono text-xs tabular-nums',
            selected ? 'text-ink/80' : 'text-fortuna/90',
          )}
        >
          +{points}p
        </span>
      )}
    </button>
  )
})
