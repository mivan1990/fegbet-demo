import { Link } from 'react-router-dom'
import { cn } from '@/lib/cn'

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      to="/"
      className={cn(
        'font-display text-xl tracking-tight text-white',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950 rounded-md',
        className,
      )}
    >
      FEG<span className="text-fortuna">BET</span>
    </Link>
  )
}
