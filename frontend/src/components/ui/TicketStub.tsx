import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface TicketStubProps {
  children: ReactNode
  /** Overlay pozitionat absolut peste tichet (ex. <Stamp />). */
  overlay?: ReactNode
  className?: string
}

/**
 * „Biletul fizic": hârtie crem, zimți semicirculari pe margini, colțuri rotunjite.
 * Conținutul (header / listă selecții / total) îl compune apelantul cu separatoare
 * `border-dashed border-ink/20`.
 */
export function TicketStub({ children, overlay, className }: TicketStubProps) {
  return (
    <div className={cn('relative', className)}>
      <div className="ticket-stub overflow-hidden rounded-2xl bg-paper text-ink shadow-card">
        {children}
      </div>
      {overlay}
    </div>
  )
}
