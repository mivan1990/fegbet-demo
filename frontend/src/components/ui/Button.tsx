import { forwardRef } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  /** Ocupa toata latimea (bare mobile, subsol de card). */
  block?: boolean
  iconLeft?: ReactNode
  iconRight?: ReactNode
}

const VARIANTS: Record<ButtonVariant, string> = {
  // CTA principal: fundal Fortuna, text ink, glow galben.
  primary:
    'bg-fortuna text-ink shadow-glow hover:brightness-[1.06] active:scale-[.98] ' +
    'disabled:hover:brightness-100 disabled:shadow-none',
  secondary:
    'bg-transparent text-white border border-white/15 hover:border-white/30 ' +
    'hover:bg-white/[.03] active:scale-[.98]',
  danger:
    'bg-bet text-white hover:brightness-[1.06] active:scale-[.98] disabled:hover:brightness-100',
  ghost:
    'bg-transparent text-white/70 hover:text-white hover:bg-white/[.05] active:scale-[.98]',
}

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-9 px-3 text-sm gap-2',
  md: 'h-11 px-4 text-sm gap-2',
  lg: 'h-13 px-6 text-base gap-2',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'secondary',
    size = 'md',
    loading = false,
    block = false,
    iconLeft,
    iconRight,
    className,
    children,
    disabled,
    type = 'button',
    ...rest
  },
  ref,
) {
  const isDisabled = disabled || loading
  return (
    <button
      ref={ref}
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={cn(
        'relative inline-flex items-center justify-center rounded-xl font-semibold',
        'transition duration-150 ease-smooth select-none',
        // zona de atingere minim 44px pe mobil chiar si pentru size sm
        'min-h-11 md:min-h-0',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna',
        'focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100',
        SIZES[size],
        VARIANTS[variant],
        block && 'w-full',
        className,
      )}
      {...rest}
    >
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center" aria-hidden>
          <Loader2 className="h-4 w-4 animate-spin" />
        </span>
      )}
      <span className={cn('inline-flex items-center gap-2', loading && 'opacity-0')}>
        {iconLeft}
        {children}
        {iconRight}
      </span>
    </button>
  )
})
