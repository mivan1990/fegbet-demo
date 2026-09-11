import { lazy, Suspense } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { Shell } from '@/components/layout'
import type { NavbarUser } from '@/components/layout'
import { useAuth } from '@/auth/AuthContext'
import { RedirectIfAuthed, RequireAdmin, RequireAuth } from '@/auth/guards'
import { Home } from '@/pages/Home'
import { NotFound } from '@/pages/NotFound'
import { Profil } from '@/pages/Profil'
import { Meciuri } from '@/pages/Meciuri'
import { Meci } from '@/pages/Meci'
import { Grupe } from '@/pages/Grupe'
import { Bracket } from '@/pages/Bracket'
import { Clasament } from '@/pages/Clasament'
import { BileteleMele } from '@/pages/BileteleMele'
import { Login } from '@/pages/auth/Login'
import { Register } from '@/pages/auth/Register'
import { AdminRoutes } from '@/pages/admin/AdminRoutes'

// Kitchen sink: doar in development (nici macar nu intra in bundle-ul de productie).
const KitchenSink = import.meta.env.DEV
  ? lazy(() => import('@/pages/KitchenSink').then((m) => ({ default: m.KitchenSink })))
  : null

export default function App() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const navbarUser: NavbarUser | null = user
    ? { displayName: user.display_name, points: user.points, isAdmin: user.is_admin }
    : null

  return (
    <Shell user={navbarUser} onLogout={logout} wide={location.pathname.startsWith('/admin')}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/meciuri" element={<Meciuri />} />
        <Route path="/meci/:id" element={<Meci />} />
        <Route path="/grupe" element={<Grupe />} />
        <Route path="/bracket" element={<Bracket />} />
        <Route path="/clasament" element={<Clasament />} />

        <Route
          path="/login"
          element={
            <RedirectIfAuthed>
              <Login />
            </RedirectIfAuthed>
          }
        />
        <Route
          path="/inregistrare"
          element={
            <RedirectIfAuthed>
              <Register />
            </RedirectIfAuthed>
          }
        />

        <Route
          path="/biletele-mele"
          element={
            <RequireAuth>
              <BileteleMele />
            </RequireAuth>
          }
        />
        <Route
          path="/profil"
          element={
            <RequireAuth>
              <Profil />
            </RequireAuth>
          }
        />

        <Route
          path="/admin/*"
          element={
            <RequireAdmin>
              <AdminRoutes />
            </RequireAdmin>
          }
        />

        {KitchenSink && (
          <Route
            path="/kitchen-sink"
            element={
              <Suspense fallback={null}>
                <KitchenSink />
              </Suspense>
            }
          />
        )}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Shell>
  )
}
