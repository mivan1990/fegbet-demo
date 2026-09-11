import { useState } from 'react'
import { ChevronLeft, ChevronRight, ListFilter, X } from 'lucide-react'
import { PageHeader } from '@/components/layout'
import { Button, Input, Select, Skeleton } from '@/components/ui'
import { cn } from '@/lib/cn'
import { useAdminLogs, useAdminUsers } from '@/api/admin'
import { formatFull } from '@/lib/datetime'
import type { LogFilters, LogItem } from '@/api/types'

const EMPTY: LogFilters = { page: 1 }

/** datetime-local (ora locală) -> ISO UTC pentru API. */
function toIso(local: string): string | null {
  if (!local) return null
  const d = new Date(local)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

function LogCard({ log }: { log: LogItem }) {
  const detail =
    log.detail && typeof log.detail === 'object'
      ? JSON.stringify(log.detail, null, 2)
      : String(log.detail ?? '')

  return (
    <li className="rounded-2xl border border-white/10 bg-navy-900 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="rounded-full bg-white/10 px-2.5 py-1 font-mono text-xs text-white/80">
          {log.action}
        </span>
        <span className="font-mono text-xs text-white/40">{formatFull(log.created_at)}</span>
      </div>
      <p className="mt-2 text-sm text-white/60">
        {log.actor_name ? (
          <span className="text-white/85">{log.actor_name}</span>
        ) : (
          <span className="text-white/40">sistem</span>
        )}
        {log.entity_type && (
          <>
            {' · '}
            {log.entity_type}
            {log.entity_id != null && ` #${log.entity_id}`}
          </>
        )}
        {log.ip_address && <span className="text-white/30"> · {log.ip_address}</span>}
      </p>
      {detail && detail !== '{}' && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-white/40 hover:text-white/70">
            detalii
          </summary>
          <pre className="scroll-x mt-2 rounded-lg bg-navy-950 p-3 text-xs text-white/70">
            {detail}
          </pre>
        </details>
      )}
    </li>
  )
}

export function AdminLogs() {
  const [filters, setFilters] = useState<LogFilters>(EMPTY)
  const [open, setOpen] = useState(false)
  const { data, isLoading, isFetching } = useAdminLogs(filters)
  const { data: users } = useAdminUsers()

  const patch = (p: Partial<LogFilters>) => setFilters((f) => ({ ...f, ...p, page: 1 }))
  const activeCount = Object.entries(filters).filter(
    ([k, v]) => k !== 'page' && v != null && v !== '',
  ).length

  const actionOptions = [
    { value: '', label: 'Toate acțiunile' },
    ...(data?.actions ?? []).map((a) => ({ value: a, label: a })),
  ]
  const userOptions = [
    { value: '', label: 'Toți utilizatorii' },
    ...(users ?? []).map((u) => ({ value: String(u.id), label: u.display_name })),
  ]

  return (
    <>
      <PageHeader
        title="Loguri"
        subtitle="Fiecare acțiune importantă, cu cine și când. 50 pe pagină, cel mai recent primul."
        action={
          <Button
            variant="secondary"
            iconLeft={<ListFilter className="h-4 w-4" />}
            onClick={() => setOpen((v) => !v)}
          >
            Filtre {activeCount > 0 && `(${activeCount})`}
          </Button>
        }
      />

      {open && (
        <div className="mb-6 space-y-4 rounded-2xl border border-white/10 bg-navy-900 p-4 md:p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Acțiune"
              options={actionOptions}
              value={filters.action ?? ''}
              onChange={(e) => patch({ action: e.target.value || null })}
            />
            <Select
              label="Utilizator"
              options={userOptions}
              value={filters.user_id ? String(filters.user_id) : ''}
              onChange={(e) => patch({ user_id: e.target.value ? Number(e.target.value) : null })}
            />
            <Input
              label="De la"
              type="datetime-local"
              onChange={(e) => patch({ from: toIso(e.target.value) })}
            />
            <Input
              label="Până la"
              type="datetime-local"
              onChange={(e) => patch({ to: toIso(e.target.value) })}
            />
          </div>
          <Input
            label="Căutare în detalii"
            placeholder="ex. nume echipă, scor…"
            defaultValue={filters.q ?? ''}
            onChange={(e) => patch({ q: e.target.value || null })}
          />
          {activeCount > 0 && (
            <Button
              variant="ghost"
              iconLeft={<X className="h-4 w-4" />}
              onClick={() => setFilters(EMPTY)}
            >
              Șterge filtrele
            </Button>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 w-full" rounded="2xl" />
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-white/50">
          Niciun log pentru filtrele astea.
        </p>
      ) : (
        <>
          <ul className={cn('space-y-3 transition', isFetching && 'opacity-60')}>
            {data.items.map((log) => (
              <LogCard key={log.id} log={log} />
            ))}
          </ul>

          <div className="mt-6 flex items-center justify-between">
            <Button
              variant="secondary"
              size="sm"
              iconLeft={<ChevronLeft className="h-4 w-4" />}
              disabled={data.page <= 1}
              onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) - 1 }))}
            >
              Înapoi
            </Button>
            <span className="font-mono text-xs text-white/50">
              pagina {data.page} / {data.pages} · {data.total} intrări
            </span>
            <Button
              variant="secondary"
              size="sm"
              iconRight={<ChevronRight className="h-4 w-4" />}
              disabled={data.page >= data.pages}
              onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))}
            >
              Înainte
            </Button>
          </div>
        </>
      )}
    </>
  )
}
