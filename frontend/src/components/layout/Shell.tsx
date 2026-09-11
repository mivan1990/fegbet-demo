import type { ReactNode } from 'react'
import { Navbar } from './Navbar'
import type { NavbarUser } from './Navbar'
import { TabBar } from './TabBar'
import { Footer } from './Footer'
import { DemoBar } from '@/demo/DemoBar'

interface ShellProps {
  children: ReactNode
  user: NavbarUser | null
  onLogout: () => void
  /** Container mai lat pe paginile de admin. */
  wide?: boolean
  /** Ascunde footer-ul (ex. pagina de pariere cu bara sticky). */
  hideFooter?: boolean
}

/** Structura globala: navbar sus, continut, tab bar jos pe mobil, footer. */
export function Shell({ children, user, onLogout, wide = false, hideFooter = false }: ShellProps) {
  return (
    <div className="flex min-h-dvh flex-col">
      <DemoBar />
      <Navbar user={user} onLogout={onLogout} />
      <main className={wide ? 'container-admin flex-1 py-6 pb-tabbar' : 'container-app flex-1 py-6 pb-tabbar'}>
        {children}
      </main>
      {!hideFooter && <Footer />}
      <TabBar />
    </div>
  )
}
