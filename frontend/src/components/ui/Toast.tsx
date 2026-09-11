import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { cn } from '@/lib/cn'

export type ToastTone = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  tone: ToastTone
  message: string
}

interface ToastContextValue {
  push: (tone: ToastTone, message: string) => void
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const MAX_VISIBLE = 3
const AUTO_DISMISS_MS = 4000

const TONE_STYLES: Record<ToastTone, { bar: string; icon: ReactNode }> = {
  success: { bar: 'bg-emerald-400', icon: <CheckCircle2 className="h-4 w-4 text-emerald-300" /> },
  error: { bar: 'bg-bet', icon: <XCircle className="h-4 w-4 text-bet-400" /> },
  info: { bar: 'bg-feg', icon: <Info className="h-4 w-4 text-feg-400" /> },
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (tone: ToastTone, message: string) => {
      const id = nextId.current++
      setItems((prev) => [...prev, { id, tone, message }].slice(-MAX_VISIBLE))
      window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS)
    },
    [dismiss],
  )

  const value = useMemo<ToastContextValue>(
    () => ({
      push,
      success: (m) => push('success', m),
      error: (m) => push('error', m),
      info: (m) => push('info', m),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className={cn(
          'pointer-events-none fixed inset-x-0 top-0 z-toast flex flex-col items-center gap-2 p-4 safe-top',
          'md:inset-x-auto md:bottom-0 md:right-0 md:top-auto md:items-end md:safe-bottom',
        )}
        role="region"
        aria-live="polite"
      >
        <AnimatePresence initial={false}>
          {items.map((t) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: -12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
              className="pointer-events-auto flex w-full max-w-sm items-start gap-3 overflow-hidden rounded-xl border border-white/10 bg-navy-800 pl-0 pr-3 py-3 shadow-card"
            >
              <span className={cn('h-full w-1 self-stretch rounded-full', TONE_STYLES[t.tone].bar)} />
              <span className="mt-1 shrink-0">{TONE_STYLES[t.tone].icon}</span>
              <p className="flex-1 text-sm text-white/90">{t.message}</p>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                aria-label="Inchide notificarea"
                className="shrink-0 rounded-md p-1 text-white/40 hover:text-white/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast trebuie folosit in interiorul <ToastProvider>')
  return ctx
}
