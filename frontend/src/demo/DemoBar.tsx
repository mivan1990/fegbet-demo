import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { DEMO_ACCOUNTS, DEMO_MODE, type DemoRole } from '@/demo/demo'

/**
 * Banda de sus care exista doar in demo-ul public.
 *
 * Rostul ei e un singur lucru: partea interesanta din aplicatie e cea de admin
 * — validezi un scor si motorul recalculeaza punctele tuturor — iar un vizitator
 * logat ca utilizator obisnuit n-ar vedea-o niciodata. De aici comuta intre roluri
 * dintr-un click, fara sa stie vreo parola.
 */
export function DemoBar() {
  const { user, loginAsDemo } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  if (!DEMO_MODE) return null

  const isAdmin = Boolean(user?.is_admin)
  const target: DemoRole = isAdmin ? 'user' : 'admin'

  const swap = async () => {
    setBusy(true)
    try {
      await loginAsDemo(target)
      navigate(target === 'admin' ? '/admin' : '/')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="border-b border-amber-400/30 bg-amber-400/10 text-amber-100">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2 text-sm">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="rounded bg-amber-400/20 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide">
            Demo
          </span>
          <span className="text-amber-100/90">
            Date inventate, turneu încheiat.
            {user ? (
              <>
                {' '}
                Ești <strong className="font-semibold">{user.display_name}</strong>
                {isAdmin ? ' (admin)' : ''}.
              </>
            ) : (
              ' Nu ești autentificat.'
            )}
          </span>
        </p>

        <button
          type="button"
          onClick={swap}
          disabled={busy}
          className="rounded-lg border border-amber-300/50 px-3 py-1 text-xs font-semibold text-amber-50 transition hover:bg-amber-300/20 disabled:opacity-50"
        >
          {busy ? 'Se comută…' : `Vezi ca ${DEMO_ACCOUNTS[target].label.toLowerCase()}`}
        </button>
      </div>
    </div>
  )
}
