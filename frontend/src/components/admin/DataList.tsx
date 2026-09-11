import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface Column<T> {
  key: string
  label: string
  render: (row: T) => ReactNode
  /** Ascunde coloana pe carduri (mobil) — de obicei pentru cea deja folosita ca titlu. */
  hideOnCard?: boolean
  align?: 'left' | 'right'
}

interface DataListProps<T> {
  rows: T[]
  columns: Column<T>[]
  rowKey: (row: T) => string | number
  cardTitle: (row: T) => ReactNode
  actions?: (row: T) => ReactNode
  /** Afisat cand nu sunt randuri. */
  empty: ReactNode
  loading?: boolean
}

/**
 * Sub 768px tabelul devine listă de carduri (PLAN_SONNET.md: „Admin — liste").
 * Peste 768px, tabel real.
 */
export function DataList<T>({
  rows,
  columns,
  rowKey,
  cardTitle,
  actions,
  empty,
  loading = false,
}: DataListProps<T>) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-2xl bg-white/5" />
        ))}
      </div>
    )
  }

  if (rows.length === 0) return <>{empty}</>

  return (
    <>
      {/* -------- Mobil: carduri -------- */}
      <ul className="space-y-3 md:hidden">
        {rows.map((row) => (
          <li
            key={rowKey(row)}
            className="rounded-2xl border border-white/10 bg-navy-900 p-4 shadow-card"
          >
            <div className="font-display text-lg text-white">{cardTitle(row)}</div>
            <dl className="mt-3 space-y-2 text-sm">
              {columns
                .filter((c) => !c.hideOnCard)
                .map((c) => (
                  <div key={c.key} className="flex items-start justify-between gap-4">
                    <dt className="text-white/45">{c.label}</dt>
                    <dd className="text-right text-white/85">{c.render(row)}</dd>
                  </div>
                ))}
            </dl>
            {actions && (
              <div className="mt-4 flex flex-col gap-2 border-t border-white/10 pt-4">
                {actions(row)}
              </div>
            )}
          </li>
        ))}
      </ul>

      {/* -------- Desktop: tabel -------- */}
      <div className="scroll-x hidden rounded-2xl border border-white/10 md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-white/40">
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={cn('px-4 py-3 font-medium', c.align === 'right' && 'text-right')}
                >
                  {c.label}
                </th>
              ))}
              {actions && <th className="px-4 py-3" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                className="border-b border-white/5 last:border-0 hover:bg-white/[.02]"
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={cn(
                      'px-4 py-3 text-white/85 align-middle',
                      c.align === 'right' && 'text-right',
                    )}
                  >
                    {c.render(row)}
                  </td>
                ))}
                {actions && (
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">{actions(row)}</div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
