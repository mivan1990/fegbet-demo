import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { LogOut, Shield, User as UserIcon } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Logo } from './Logo'
import { NAV_ITEMS } from './navItems'

export interface NavbarUser {
  displayName: string
  points: number
  isAdmin: boolean
}

interface NavbarProps {
  user: NavbarUser | null
  onLogout: () => void
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function PointsChip({ points }: { points: number }) {
  return (
    <span className="inline-flex items-center rounded-full bg-fortuna px-3 py-1 font-mono text-sm font-semibold tabular-nums text-ink">
      {points}p
    </span>
  )
}

function UserMenu({ user, onLogout }: { user: NavbarUser; onLogout: () => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Meniu cont"
        className="flex h-11 w-11 items-center justify-center rounded-full border border-white/15 bg-navy-800 font-mono text-sm font-semibold text-white hover:border-white/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950"
      >
        {initials(user.displayName)}
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-52 overflow-hidden rounded-xl border border-white/10 bg-navy-800 py-2 shadow-card"
        >
          <div className="px-4 py-2 text-xs uppercase tracking-wider text-white/40">
            {user.displayName}
          </div>
          <MenuLink to="/profil" icon={UserIcon} onClick={() => setOpen(false)}>
            Profil
          </MenuLink>
          {user.isAdmin && (
            <MenuLink to="/admin" icon={Shield} onClick={() => setOpen(false)}>
              Administrare
            </MenuLink>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false)
              onLogout()
            }}
            className="flex w-full items-center gap-3 px-4 py-2 text-left text-sm text-white/80 hover:bg-white/5"
          >
            <LogOut className="h-4 w-4" aria-hidden />
            Iesire
          </button>
        </div>
      )}
    </div>
  )
}

function MenuLink({
  to,
  icon: Icon,
  onClick,
  children,
}: {
  to: string
  icon: LucideIcon
  onClick: () => void
  children: ReactNode
}) {
  return (
    <Link
      to={to}
      role="menuitem"
      onClick={onClick}
      className="flex items-center gap-3 px-4 py-2 text-sm text-white/80 hover:bg-white/5"
    >
      <Icon className="h-4 w-4" aria-hidden />
      {children}
    </Link>
  )
}

export function Navbar({ user, onLogout }: NavbarProps) {
  return (
    <header className="sticky top-0 z-navbar border-b border-white/10 bg-navy-950/80 backdrop-blur safe-top">
      <div className="container-app flex h-16 items-center justify-between gap-4">
        <Logo />

        <nav className="hidden items-center gap-1 md:flex">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'rounded-xl px-3 py-2 text-sm font-medium transition duration-150',
                  isActive ? 'bg-white/10 text-white' : 'text-white/60 hover:text-white',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <PointsChip points={user.points} />
              <UserMenu user={user} onLogout={onLogout} />
            </>
          ) : (
            <>
              <LinkButton to="/login">Intra</LinkButton>
              <LinkButton to="/inregistrare" primary>
                Cont nou
              </LinkButton>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

function LinkButton({
  to,
  primary,
  className,
  children,
}: {
  to: string
  primary?: boolean
  className?: string
  children: ReactNode
}) {
  return (
    <Link
      to={to}
      className={cn(
        'inline-flex min-h-11 items-center justify-center rounded-xl px-4 text-sm font-semibold transition duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950',
        primary
          ? 'bg-fortuna text-ink shadow-glow hover:brightness-[1.06]'
          : 'border border-white/15 text-white hover:border-white/30',
        className,
      )}
    >
      {children}
    </Link>
  )
}
