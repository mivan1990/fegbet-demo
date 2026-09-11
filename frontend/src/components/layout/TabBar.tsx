import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { NAV_ITEMS } from './navItems'

/**
 * Bara de navigatie de jos, doar pe mobil (< md). Se pariaza de pe telefon,
 * deci navigatia principala sta la degetul mare. Respecta safe-area iOS.
 */
export function TabBar() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-navbar border-t border-white/10 bg-navy-950/90 backdrop-blur safe-bottom md:hidden"
      aria-label="Navigatie principala"
    >
      <ul className="grid grid-cols-5">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-14 flex-col items-center justify-center gap-1 px-2 py-2 text-xs font-medium transition duration-150',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-fortuna',
                    isActive ? 'text-fortuna' : 'text-white/55',
                  )
                }
              >
                <Icon className="h-5 w-5" aria-hidden />
                <span className="truncate">{item.label}</span>
              </NavLink>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
