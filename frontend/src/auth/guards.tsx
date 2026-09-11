import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { useToast } from '@/components/ui'
import { Skeleton } from '@/components/ui'

function FullPageLoading() {
  return (
    <div className="space-y-4 py-8">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-40 w-full" rounded="2xl" />
      <Skeleton className="h-40 w-full" rounded="2xl" />
    </div>
  )
}

/** Rute care cer autentificare. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <FullPageLoading />
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <>{children}</>
}

/** Rute /admin/* — cer `user.is_admin`. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { status, user } = useAuth()
  const toast = useToast()
  const warned = useRef(false)

  useEffect(() => {
    if (status === 'authenticated' && user && !user.is_admin && !warned.current) {
      warned.current = true
      toast.info('Zona asta e doar pentru șefi.')
    }
  }, [status, user, toast])

  if (status === 'loading') return <FullPageLoading />
  if (status === 'anonymous') return <Navigate to="/login" replace />
  if (!user?.is_admin) return <Navigate to="/" replace />
  return <>{children}</>
}

/** Login/inregistrare: daca esti deja logat, du-te acasa. */
export function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === 'authenticated') return <Navigate to="/" replace />
  return <>{children}</>
}
