import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  eyebrow?: ReactNode
  title?: ReactNode
  footer?: ReactNode
  /** Culoare de accent a marginii (o singura culoare per card, niciodata trei). */
  accent?: 'none' | 'fortuna' | 'bet' | 'feg'
  children?: ReactNode
}

const ACCENT: Record<NonNullable<CardProps['accent']>, string> = {
  none: 'border-white/10',
  fortuna: 'border-fortuna/60',
  bet: 'border-bet/40',
  feg: 'border-feg/40',
}

export function Card({
  eyebrow,
  title,
  footer,
  accent = 'none',
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border bg-navy-900 p-4 shadow-card md:p-6',
        ACCENT[accent],
        className,
      )}
      {...rest}
    >
      {eyebrow && (
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/45">
          {eyebrow}
        </div>
      )}
      {title && <h3 className="font-display text-lg text-white md:text-xl">{title}</h3>}
      {children && <div className={cn((title || eyebrow) && 'mt-3')}>{children}</div>}
      {footer && <div className="mt-4 border-t border-white/10 pt-4">{footer}</div>}
    </div>
  )
}
