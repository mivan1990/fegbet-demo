import { useEffect, useState } from 'react'
import { parseUtc } from './datetime'

export const URGENT_THRESHOLD_MS = 15 * 60 * 1000

export interface CountdownState {
  totalMs: number
  days: number
  hours: number
  minutes: number
  seconds: number
  isExpired: boolean
  /** Sub 15 minute pana la start (si nu expirat). */
  isUrgent: boolean
  /** "04:12" cand e urgent, altfel "2z 4h 10m". */
  label: string
}

function compute(targetMs: number | null, nowMs: number): CountdownState {
  if (targetMs == null) {
    return {
      totalMs: 0, days: 0, hours: 0, minutes: 0, seconds: 0,
      isExpired: false, isUrgent: false, label: '—',
    }
  }
  const totalMs = Math.max(0, targetMs - nowMs)
  const isExpired = totalMs <= 0
  const totalSec = Math.floor(totalMs / 1000)
  const days = Math.floor(totalSec / 86400)
  const hours = Math.floor((totalSec % 86400) / 3600)
  const minutes = Math.floor((totalSec % 3600) / 60)
  const seconds = totalSec % 60
  const isUrgent = !isExpired && totalMs <= URGENT_THRESHOLD_MS

  let label: string
  if (isExpired) {
    label = '00:00'
  } else if (isUrgent) {
    label = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  } else if (days > 0) {
    label = `${days}z ${hours}h ${minutes}m`
  } else {
    label = `${hours}h ${minutes}m ${seconds}s`
  }

  return { totalMs, days, hours, minutes, seconds, isExpired, isUrgent, label }
}

/**
 * Countdown live. Tick la 1s cand e urgent (afisam secunde), altfel la 30s.
 * `target` este ISO UTC de la server.
 */
export function useCountdown(target: string | null | undefined): CountdownState {
  const targetMs = parseUtc(target)?.getTime() ?? null
  const [state, setState] = useState<CountdownState>(() => compute(targetMs, Date.now()))

  useEffect(() => {
    if (targetMs == null) {
      setState(compute(null, Date.now()))
      return
    }
    const tick = () => setState(compute(targetMs, Date.now()))
    tick()
    const remaining = targetMs - Date.now()
    const interval = remaining <= URGENT_THRESHOLD_MS + 1000 ? 1000 : 30000
    const id = window.setInterval(tick, interval)
    return () => window.clearInterval(id)
  }, [targetMs, state.isUrgent])

  return state
}
