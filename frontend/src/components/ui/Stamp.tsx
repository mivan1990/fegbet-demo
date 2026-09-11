import { cn } from '@/lib/cn'
import type { TicketVerdict } from '@/lib/ticket'

const STAMP: Record<TicketVerdict, { label: string; cls: string }> = {
  won: { label: 'CÂȘTIGAT', cls: 'text-emerald-400 border-emerald-400' },
  partial: { label: 'PARȚIAL', cls: 'text-fortuna border-fortuna' },
  lost: { label: 'PIERDUT', cls: 'text-bet-400 border-bet-400' },
}

/**
 * Stampila care cade peste bilet dupa decontare: rotita -12°, animatie de „impact"
 * (scale 1.4 → 1). Verde CÂȘTIGAT / galben PARȚIAL / roșu PIERDUT.
 */
export function Stamp({ verdict, className }: { verdict: TicketVerdict; className?: string }) {
  const s = STAMP[verdict]
  return (
    <div
      className={cn('pointer-events-none absolute inset-0 flex items-center justify-center', className)}
      data-testid="stamp"
      aria-hidden
    >
      <span
        className={cn(
          'select-none rounded-xl border-4 px-5 py-1.5 font-display text-3xl font-extrabold uppercase tracking-widest',
          '-rotate-12 opacity-85 motion-safe:animate-stamp-in',
          s.cls,
        )}
      >
        {s.label}
      </span>
    </div>
  )
}
