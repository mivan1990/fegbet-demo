import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/cn'

export type BadgeTone = 'neutral' | 'success' | 'urgent' | 'info'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  /** Pulsare — permisa DOAR pe countdown-ul urgent sub 15 min. */
  pulse?: boolean
  children: ReactNode
}

const TONES: Record<BadgeTone, string> = {
  neutral: 'bg-white/10 text-white/80',
  success: 'bg-emerald-500/15 text-emerald-300',
  urgent: 'bg-bet/15 text-bet-400',
  info: 'bg-feg/15 text-feg-400',
}

export function Badge({ tone = 'neutral', pulse = false, className, children, ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide',
        TONES[tone],
        pulse && 'motion-safe:animate-pulse-urgent',
        className,
      )}
      {...rest}
    >
      {children}
    </span>
  )
}
