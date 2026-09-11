import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  /** Colturi rotunjite ca elementul real pe care il inlocuieste. */
  rounded?: 'xl' | '2xl' | 'full'
}

/**
 * Placeholder cu shimmer. Layout-ul nu trebuie sa sara cand sosesc datele,
 * deci Skeleton-ul are exact dimensiunea continutului real (o dai prin className).
 */
export function Skeleton({ rounded = 'xl', className, ...rest }: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={cn(
        'relative overflow-hidden bg-white/5',
        rounded === 'xl' && 'rounded-xl',
        rounded === '2xl' && 'rounded-2xl',
        rounded === 'full' && 'rounded-full',
        className,
      )}
      {...rest}
    >
      <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent motion-safe:animate-shimmer" />
    </div>
  )
}

/** Schelet de card de meci — folosit in listele care se incarca. */
export function MatchCardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/10 bg-navy-900 p-4 shadow-card md:p-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-6 w-20" rounded="full" />
      </div>
      <div className="mt-6 flex items-center justify-between gap-4">
        <Skeleton className="h-6 w-28" />
        <Skeleton className="h-6 w-10" />
        <Skeleton className="h-6 w-28" />
      </div>
      <Skeleton className="mt-6 h-4 w-52" />
      <Skeleton className="mt-3 h-11 w-full" />
    </div>
  )
}
