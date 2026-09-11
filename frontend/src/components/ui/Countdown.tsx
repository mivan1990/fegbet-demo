import { useEffect, useRef } from 'react'
import { Lock } from 'lucide-react'
import { useCountdown } from '@/lib/countdown'
import { Badge } from './Badge'
import { cn } from '@/lib/cn'

interface CountdownProps {
  /** ISO UTC de la server. */
  target: string | null | undefined
  /** Text afisat cand a expirat. */
  expiredLabel?: string
  className?: string
  /** Apelat o singura data cand countdown-ul atinge 0 cat utilizatorul e pe pagina. */
  onExpire?: () => void
}

/**
 * Sub 15 minute: badge rosu care pulseaza, „SE ÎNCHIDE ÎN 04:12" (mono, tabular-nums).
 * La 0: badge neutru cu lacat. Peste 15 min: badge neutru cu timpul ramas.
 */
export function Countdown({ target, expiredLabel = 'Meciul a început', className, onExpire }: CountdownProps) {
  const c = useCountdown(target)
  const firedExpire = useRef(false)

  useEffect(() => {
    if (c.isExpired && target && !firedExpire.current) {
      firedExpire.current = true
      onExpire?.()
    }
  }, [c.isExpired, target, onExpire])

  if (!target) {
    return (
      <Badge tone="neutral" className={className}>
        <Lock className="h-3 w-3" aria-hidden />
        Data nestabilită
      </Badge>
    )
  }

  if (c.isExpired) {
    return (
      <Badge tone="neutral" className={className}>
        <Lock className="h-3 w-3" aria-hidden />
        {expiredLabel}
      </Badge>
    )
  }

  if (c.isUrgent) {
    return (
      <Badge tone="urgent" pulse className={cn('font-mono', className)}>
        <Lock className="h-3 w-3" aria-hidden />
        <span>SE ÎNCHIDE ÎN </span>
        <span className="tabular-nums">{c.label}</span>
      </Badge>
    )
  }

  return (
    <Badge tone="neutral" className={cn('font-mono', className)}>
      <span className="tabular-nums">{c.label}</span>
    </Badge>
  )
}
