import axios, { AxiosError, type AxiosInstance } from 'axios'

const TOKEN_KEY = 'fegbet.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* localStorage indisponibil (mod privat) — mergem mai departe fara persistenta */
  }
}

export const api: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/** Handler setat de AuthProvider: ce se face cand serverul raspunde 401. */
let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn
}

api.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError) => {
    const status = error.response?.status
    const url = error.config?.url ?? ''
    // 401 pe rute protejate => sesiune expirata. Nu si pe login/register/me (le tratam local).
    const isAuthProbe = url.includes('/auth/login') || url.includes('/auth/register')
    if (status === 401 && !isAuthProbe) {
      setToken(null)
      onUnauthorized?.()
    }
    return Promise.reject(error)
  },
)

/** Extrage mesajul din raspunsul de eroare al API-ului (mereu `{detail: string}`). */
export function apiErrorMessage(error: unknown, fallback = 'Ceva n-a mers. Mai încearcă.'): string {
  if (error instanceof AxiosError) {
    if (error.response?.data && typeof error.response.data === 'object') {
      const detail = (error.response.data as { detail?: unknown }).detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: string }
        if (first?.msg) return first.msg
      }
    }
    if (error.code === 'ERR_NETWORK') return 'Am pierdut mingea. Mai încearcă.'
  }
  return fallback
}
