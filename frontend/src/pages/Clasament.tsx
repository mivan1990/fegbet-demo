import { useState } from 'react'
import { ChevronDown, Crown, Trophy } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { EmptyState, Skeleton } from '@/components/ui'
import { cn } from '@/lib/cn'
import { useAuth } from '@/auth/AuthContext'
import { useLeaderboard } from '@/api/leaderboard'
import type { LeaderboardRow } from '@/api/types'

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function winRate(row: LeaderboardRow): string {
  if (row.total_selections === 0) return '—'
  return `${Math.round((row.correct_selections / row.total_selections) * 100)}%`
}

/** Culoarea medaliei: aur / argint / bronz, peste albastru. */
const MEDAL: Record<number, { ring: string; text: string; label: string }> = {
  1: { ring: 'border-fortuna bg-fortuna/10', text: 'text-fortuna', label: 'Aur' },
  2: { ring: 'border-slate-300 bg-slate-300/10', text: 'text-slate-200', label: 'Argint' },
  3: { ring: 'border-amber-600 bg-amber-600/10', text: 'text-amber-500', label: 'Bronz' },
}

function PodiumStep({ row, isMe, solo }: { row: LeaderboardRow; isMe: boolean; solo: boolean }) {
  const medal = MEDAL[row.rank] ?? MEDAL[3]
  // Inaltimi diferite: locul 1 cel mai inalt.
  const height = row.rank === 1 ? 'h-24 md:h-32' : row.rank === 2 ? 'h-16 md:h-24' : 'h-12 md:h-20'
  // Aranjare clasica de podium: 2 – 1 – 3. Cu mai putini de 3, ordine naturala.
  const order = solo ? '' : row.rank === 1 ? 'order-2' : row.rank === 2 ? 'order-1' : 'order-3'

  return (
    <div className={cn('flex w-24 flex-col items-center gap-2 md:w-32', order)}>
      <div
        className={cn(
          'relative flex h-12 w-12 items-center justify-center rounded-full border-2 font-mono text-sm font-bold md:h-14 md:w-14',
          medal.ring,
          medal.text,
        )}
      >
        {initials(row.display_name)}
        {row.rank === 1 && (
          <Crown className="absolute -top-4 h-5 w-5 text-fortuna" aria-hidden />
        )}
      </div>
      <div className="w-full text-center">
        <p className={cn('truncate text-sm font-semibold', isMe ? 'text-fortuna' : 'text-white')}>
          {row.display_name}
        </p>
        <p className="font-mono text-xs tabular-nums text-white/50">{row.points}p</p>
        {row.group_points > 0 && (
          <p className="text-[11px] text-white/35">din care {row.group_points} p. din grupe</p>
        )}
      </div>
      <div
        className={cn(
          'flex w-full items-center justify-center rounded-t-xl border-x border-t',
          height,
          medal.ring,
        )}
      >
        <span className={cn('font-display text-2xl md:text-3xl', medal.text)}>{row.rank}</span>
      </div>
    </div>
  )
}

function Row({ row, isMe }: { row: LeaderboardRow; isMe: boolean }) {
  const [open, setOpen] = useState(false)
  return (
    <li
      className={cn(
        'rounded-2xl border bg-navy-900',
        isMe ? 'border-fortuna/50' : 'border-white/10',
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna focus-visible:ring-inset"
      >
        <span className="w-6 shrink-0 text-center font-mono text-sm tabular-nums text-white/45">
          {row.rank}
        </span>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-navy-800 font-mono text-xs font-semibold text-white/80">
          {initials(row.display_name)}
        </span>
        <span className="min-w-0 flex-1">
          <span className={cn('block truncate font-semibold', isMe ? 'text-fortuna' : 'text-white')}>
            {row.display_name}
            {isMe && <span className="ml-2 text-xs font-normal text-white/40">(tu)</span>}
          </span>
          {row.group_points > 0 && (
            <span className="block text-xs text-white/40">din care {row.group_points} p. din grupe</span>
          )}
        </span>
        <span className="shrink-0 font-mono text-sm font-semibold tabular-nums text-fortuna">
          {row.points}p
        </span>
        <ChevronDown
          className={cn('h-4 w-4 shrink-0 text-white/30 transition', open && 'rotate-180')}
          aria-hidden
        />
      </button>
      {open && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-white/10 px-4 py-3 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs text-white/40">Bilete</dt>
            <dd className="font-mono tabular-nums text-white/85">{row.tickets}</dd>
          </div>
          <div>
            <dt className="text-xs text-white/40">Decontate</dt>
            <dd className="font-mono tabular-nums text-white/85">{row.settled_tickets}</dd>
          </div>
          <div>
            <dt className="text-xs text-white/40">Bilete pe plus</dt>
            <dd className="font-mono tabular-nums text-white/85">{row.won_tickets}</dd>
          </div>
          <div>
            <dt className="text-xs text-white/40">Reușită selecții</dt>
            <dd className="font-mono tabular-nums text-white/85">
              {winRate(row)}
              <span className="ml-1 text-white/40">
                ({row.correct_selections}/{row.total_selections})
              </span>
            </dd>
          </div>
          {row.total_qualifiers > 0 && (
            <div>
              <dt className="text-xs text-white/40">Calificări ghicite</dt>
              <dd className="font-mono tabular-nums text-white/85">
                {row.correct_qualifiers}/{row.total_qualifiers}
              </dd>
            </div>
          )}
        </dl>
      )}
    </li>
  )
}

export function Clasament() {
  const { user } = useAuth()
  const { data, isLoading, isError } = useLeaderboard()
  const myName = user?.display_name ?? null

  if (isLoading) {
    return (
      <>
        <PageHeader title="Clasament" subtitle="Cine adună cele mai multe puncte din bilete." />
        <Skeleton className="h-48 w-full" rounded="2xl" />
        <div className="mt-6 space-y-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-14 w-full" rounded="2xl" />
          ))}
        </div>
      </>
    )
  }

  if (isError || !data || data.length === 0) {
    return (
      <>
        <PageHeader title="Clasament" subtitle="Cine adună cele mai multe puncte din bilete." />
        <EmptyState
          icon={Trophy}
          title="Clasament gol"
          line="Nimeni n-a decontat niciun bilet încă. Fii tu primul pe podium."
        />
      </>
    )
  }

  const podium = data.slice(0, 3)
  const rest = data.slice(3)
  const last = data.length > 3 ? data[data.length - 1] : null

  return (
    <>
      <PageHeader title="Clasament" subtitle="Cine adună cele mai multe puncte din bilete." />

      {/* -------- Podium -------- */}
      <section className="rounded-2xl border border-white/10 bg-navy-900 p-4 pt-8 shadow-card md:p-6 md:pt-10">
        <div className="flex items-end justify-center gap-3 md:gap-4">
          {podium.map((r) => (
            <PodiumStep
              key={r.rank}
              row={r}
              isMe={r.display_name === myName}
              solo={podium.length < 3}
            />
          ))}
        </div>
        <p className="mt-4 text-center text-sm text-fortuna">
          {podium[0]?.display_name} — Regele biletelor 👑
        </p>
      </section>

      {/* -------- Restul -------- */}
      {rest.length > 0 && (
        <ul className="mt-6 space-y-2">
          {rest.map((r) => (
            <Row key={r.rank} row={r} isMe={r.display_name === myName} />
          ))}
        </ul>
      )}

      {last && (
        <p className="mt-4 text-center text-sm text-white/40">
          {last.display_name} — Ghinionistul serviciului 🫠
        </p>
      )}
    </>
  )
}
