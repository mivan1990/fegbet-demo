import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/cn'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  /** Un rand amuzant, niciodata doar "No data". */
  line: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon: Icon, title, line, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 px-6 py-12 text-center',
        className,
      )}
    >
      <Icon className="h-12 w-12 text-white/20" strokeWidth={1.5} aria-hidden />
      <p className="mt-4 font-display text-lg text-white">{title}</p>
      <p className="mt-2 max-w-sm text-sm text-white/50">{line}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
