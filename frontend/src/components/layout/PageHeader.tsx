import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  /** Actiune in dreapta titlului (buton), pe desktop. */
  action?: ReactNode
}

/** Titlu de pagina consecvent: h1 mare + o linie de subtitlu. */
export function PageHeader({ title, subtitle, action }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-3xl text-white md:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 text-white/50">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
