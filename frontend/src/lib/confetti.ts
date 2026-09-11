import confetti from 'canvas-confetti'

const STORAGE_PREFIX = 'fegbet.confetti.'
const GROUP_STORAGE_PREFIX = 'fegbet.confetti.group.'

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
  )
}

function markSeenOnce(key: string): boolean {
  try {
    if (localStorage.getItem(key)) return false
    localStorage.setItem(key, '1')
  } catch {
    /* localStorage indisponibil — tot dăm confetti, doar că se poate repeta */
  }
  return true
}

function burst(): void {
  const fire = (particleRatio: number, opts: confetti.Options) =>
    confetti({
      origin: { y: 0.7 },
      colors: ['#FFC800', '#1E5BFF', '#F03A2E', '#FBF7EE'],
      disableForReducedMotion: true,
      particleCount: Math.floor(180 * particleRatio),
      ...opts,
    })

  fire(0.25, { spread: 26, startVelocity: 55 })
  fire(0.2, { spread: 60 })
  fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8 })
  fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2 })
  fire(0.1, { spread: 120, startVelocity: 45 })
}

/**
 * Confetti la deschiderea unui bilet câștigător — o singură dată per bilet
 * (ține minte în localStorage). Nu se declanșează cu prefers-reduced-motion.
 */
export function celebrateTicketOnce(ticketId: number): void {
  if (prefersReducedMotion()) return
  if (!markSeenOnce(`${STORAGE_PREFIX}${ticketId}`)) return
  burst()
}

/**
 * Aceeași convenție, pentru un pronostic de grupă câștigător — o singură dată
 * per pronostic. Cheie separată de cea a biletelor, ca id-urile să nu se calce.
 */
export function celebrateGroupPredictionOnce(predictionId: number): void {
  if (prefersReducedMotion()) return
  if (!markSeenOnce(`${GROUP_STORAGE_PREFIX}${predictionId}`)) return
  burst()
}
