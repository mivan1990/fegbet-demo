import { forwardRef, useId } from 'react'
import type { InputHTMLAttributes, ReactNode } from 'react'
import { AlertCircle } from 'lucide-react'
import { cn } from '@/lib/cn'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Label deasupra, mereu vizibil (nu placeholder-as-label). */
  label: string
  error?: string | null
  hint?: ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, id, className, ...rest },
  ref,
) {
  const autoId = useId()
  const inputId = id ?? autoId
  const errId = `${inputId}-err`
  const hintId = `${inputId}-hint`

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={inputId} className="text-sm font-medium text-white/80">
        {label}
      </label>
      <input
        ref={ref}
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={cn(error && errId, hint && hintId) || undefined}
        className={cn(
          'h-11 rounded-xl bg-navy-800 px-4 text-base text-white placeholder:text-white/35',
          'border transition duration-150 ease-smooth',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-fortuna',
          'focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950',
          'disabled:opacity-40 disabled:cursor-not-allowed',
          error ? 'border-bet' : 'border-white/10 focus:border-white/25',
          className,
        )}
        {...rest}
      />
      {hint && !error && (
        <p id={hintId} className="text-xs text-white/45">
          {hint}
        </p>
      )}
      {error && (
        <p id={errId} className="flex items-center gap-1 text-xs font-medium text-bet-400">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden />
          {error}
        </p>
      )}
    </div>
  )
})
