import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Button } from './Button'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  /** Butoane de actiune, fixate jos (si pe mobil, deasupra safe-area). */
  footer?: ReactNode
  /**
   * Pe mobil devine ecran complet cu header fix + continut scrollabil + actiuni jos
   * (necesar pentru validarea meciului de pe telefon). Implicit true.
   */
  fullScreenOnMobile?: boolean
}

/** Modal propriu. Nu folosim niciodata alert()/confirm()/prompt(). */
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  fullScreenOnMobile = true,
}: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open, onClose])

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-modal flex items-stretch justify-center md:items-center md:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <button
            type="button"
            aria-label="Inchide"
            onClick={onClose}
            className="absolute inset-0 bg-navy-950/70 backdrop-blur-sm"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
            className={cn(
              'relative flex w-full flex-col bg-navy-900 shadow-card',
              'md:max-w-lg md:rounded-2xl md:border md:border-white/10',
              fullScreenOnMobile
                ? 'h-dvh md:h-auto md:max-h-modal'
                : 'm-4 max-h-modal self-center rounded-2xl border border-white/10',
            )}
          >
            <header className="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 px-4 py-4 safe-top md:px-6">
              <h2 className="font-display text-lg text-white">{title}</h2>
              <button
                type="button"
                onClick={onClose}
                aria-label="Inchide"
                className="rounded-md p-1 text-white/50 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fortuna"
              >
                <X className="h-5 w-5" />
              </button>
            </header>

            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 md:px-6">{children}</div>

            {footer && (
              <footer className="flex shrink-0 flex-col-reverse gap-2 border-t border-white/10 px-4 py-4 safe-bottom sm:flex-row sm:justify-end md:px-6">
                {footer}
              </footer>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  )
}

/** Confirmare — inlocuieste window.confirm(). */
interface ConfirmDialogProps {
  open: boolean
  title: string
  message: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
  loading?: boolean
  onConfirm: () => void
  onClose: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Renunta',
  danger = false,
  loading = false,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      fullScreenOnMobile={false}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={danger ? 'danger' : 'primary'}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm text-white/70">{message}</p>
    </Modal>
  )
}
