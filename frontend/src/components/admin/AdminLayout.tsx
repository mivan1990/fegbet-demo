import { NavLink, Outlet } from 'react-router-dom'
import {
  CalendarRange,
  LayoutDashboard,
  ScrollText,
  Shield,
  SlidersHorizontal,
  UserCog,
  Users,
  Users2,
} from 'lucide-react'
import { cn } from '@/lib/cn'

const TABS = [
  { to: '/admin', label: 'Panou', icon: LayoutDashboard, end: true },
  { to: '/admin/meciuri', label: 'Meciuri', icon: CalendarRange, end: false },
  { to: '/admin/grupe', label: 'Grupe', icon: Users2, end: false },
  { to: '/admin/echipe', label: 'Echipe', icon: Shield, end: false },
  { to: '/admin/jucatori', label: 'Jucători', icon: Users, end: false },
  { to: '/admin/utilizatori', label: 'Utilizatori', icon: UserCog, end: false },
  { to: '/admin/loguri', label: 'Loguri', icon: ScrollText, end: false },
  { to: '/admin/setari', label: 'Setări', icon: SlidersHorizontal, end: false },
]

export function AdminLayout() {
  return (
    <div>
      <div className="mb-6 flex items-center gap-2 text-sm text-white/40">
        <Shield className="h-4 w-4" />
        <span className="uppercase tracking-wider">Administrare</span>
      </div>

      <nav className="scroll-x mb-8 -mx-4 flex gap-2 px-4 md:mx-0 md:px-0">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              cn(
                'flex shrink-0 items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition duration-150',
                isActive
                  ? 'border-fortuna/60 bg-fortuna/10 text-white'
                  : 'border-white/10 text-white/60 hover:text-white',
              )
            }
          >
            <tab.icon className="h-4 w-4" aria-hidden />
            {tab.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  )
}
