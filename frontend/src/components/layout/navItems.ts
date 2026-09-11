import type { LucideIcon } from 'lucide-react'
import { CalendarDays, ListChecks, Trophy, GitBranch, Users2 } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

/** Navigatia principala: centru pe desktop, tab bar jos pe mobil. */
export const NAV_ITEMS: NavItem[] = [
  { to: '/meciuri', label: 'Meciuri', icon: CalendarDays },
  { to: '/grupe', label: 'Grupe', icon: Users2 },
  { to: '/bracket', label: 'Bracket', icon: GitBranch },
  { to: '/biletele-mele', label: 'Biletele mele', icon: ListChecks },
  { to: '/clasament', label: 'Clasament', icon: Trophy },
]
