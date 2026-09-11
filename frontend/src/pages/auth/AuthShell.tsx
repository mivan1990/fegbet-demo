import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

interface AuthShellProps {
  title: string
  subtitle: string
  children: ReactNode
  footer: ReactNode
}

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col py-8 md:py-16">
      <Link to="/" className="mb-8 self-center font-display text-2xl text-white">
        FEG<span className="text-fortuna">BET</span>
      </Link>
      <div className="rounded-2xl border border-white/10 bg-navy-900 p-6 shadow-card">
        <h1 className="font-display text-2xl text-white">{title}</h1>
        <p className="mt-2 text-sm text-white/50">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
      <div className="mt-6 text-center text-sm text-white/50">{footer}</div>
    </div>
  )
}
