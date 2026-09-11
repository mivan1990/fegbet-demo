import { forwardRef, useId } from 'react'
import type { SelectHTMLAttributes, ReactNode } from 'react'
import { AlertCircle, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/cn'

interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label: string
  options: SelectOption[]
  error?: string | null
  hint?: ReactNode
  placeholder?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, options, error, hint, placeholder, id, className, ...rest },
  ref,
) {
  const autoId = useId()
  const selectId = id ?? autoId
  const errId = `${selectId}-err`

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={selectId} className="text-sm font-medium text-white/80">
        {label}
      </label>
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errId : undefined}
          className={cn(
            'h-11 w-full appearance-none rounded-xl bg-navy-800 pl-4 pr-10 text-base text-white',
            'border transition duration-150 ease-smooth',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-fortuna',
            'focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            error ? 'border-bet' : 'border-white/10 focus:border-white/25',
            className,
          )}
          {...rest}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((o) => (
            <option key={o.value} value={o.value} className="bg-navy-800 text-white">
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/45"
          aria-hidden
        />
      </div>
      {hint && !error && <p className="text-xs text-white/45">{hint}</p>}
      {error && (
        <p id={errId} className="flex items-center gap-1 text-xs font-medium text-bet-400">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden />
          {error}
        </p>
      )}
    </div>
  )
})
