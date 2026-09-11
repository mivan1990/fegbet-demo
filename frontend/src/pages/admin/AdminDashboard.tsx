import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Card, Skeleton } from '@/components/ui'
import { useAdminStats } from '@/api/admin'

const MARKET_LABELS: Record<string, string> = {
  WINNER: 'Cine câștigă',
  QUALIFY: 'Cine merge mai departe',
  TOTAL_GOALS: 'Total goluri',
  BTTS: 'Ambele marchează',
  SCORER: 'Marcator FEG',
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wider text-white/45">{label}</p>
      <p className="mt-2 font-display text-3xl tabular-nums text-white">{value}</p>
    </Card>
  )
}

export function AdminDashboard() {
  const { data, isLoading } = useAdminStats()

  return (
    <>
      <PageHeader title="Panou de control" subtitle="Cifrele turneului, pe scurt." />

      {isLoading || !data ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24" rounded="2xl" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Stat label="Utilizatori" value={data.users} />
          <Stat label="Echipe" value={data.teams} />
          <Stat label="Jucători FEG" value={data.players} />
          <Stat label="Meciuri" value={data.matches} />
          <Stat label="Meciuri validate" value={data.matches_settled} />
          <Stat label="Bilete plasate" value={data.tickets} />
          <Stat
            label="Piața cea mai jucată"
            value={data.top_market ? (MARKET_LABELS[data.top_market] ?? data.top_market) : '—'}
          />
        </div>
      )}

      <div className="mt-8 grid gap-3 sm:grid-cols-3">
        <QuickLink to="/admin/meciuri" label="Meciuri & bracket" />
        <QuickLink to="/admin/echipe" label="Echipe" />
        <QuickLink to="/admin/jucatori" label="Jucători FEG" />
        <QuickLink to="/admin/utilizatori" label="Utilizatori" />
        <QuickLink to="/admin/loguri" label="Loguri" />
        <QuickLink to="/admin/setari" label="Setări punctaje" />
      </div>
    </>
  )
}

function QuickLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between rounded-2xl border border-white/10 bg-navy-900 p-4 text-white/80 transition duration-150 hover:border-white/25 hover:text-white"
    >
      {label}
      <ArrowRight className="h-4 w-4" />
    </Link>
  )
}
