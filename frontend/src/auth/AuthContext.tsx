import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken, setUnauthorizedHandler, getToken } from '@/api/client'
import type { AuthUser, TokenResponse } from '@/api/types'
import { useToast } from '@/components/ui'
import { DEMO_ACCOUNTS, DEMO_MODE, hasOptedOut, setOptedOut, type DemoRole } from '@/demo/demo'

type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

interface AuthContextValue {
  user: AuthUser | null
  status: AuthStatus
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
  /** Doar in demo-ul public: intra cu unul dintre cele doua conturi gata facute. */
  loginAsDemo: (role: DemoRole) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  // In demo pornim tot pe „loading" chiar fara token: urmeaza auto-login-ul, iar
  // altfel ecranul ar clipi o clipa in starea de nelogat.
  const [status, setStatus] = useState<AuthStatus>(() =>
    getToken() || (DEMO_MODE && !hasOptedOut()) ? 'loading' : 'anonymous',
  )
  const navigate = useNavigate()
  const toast = useToast()
  const bootstrapped = useRef(false)

  const applyToken = useCallback((res: TokenResponse) => {
    setToken(res.access_token)
    setUser(res.user)
    setStatus('authenticated')
  }, [])

  const loginAsDemo = useCallback(
    async (role: DemoRole) => {
      const account = DEMO_ACCOUNTS[role]
      const { data } = await api.post<TokenResponse>('/auth/login', {
        email: account.email,
        password: account.password,
      })
      setOptedOut(false)
      applyToken(data)
    },
    [applyToken],
  )

  const refresh = useCallback(async () => {
    if (!getToken()) {
      // Demo public: intram singuri cu contul de vizitator. Daca omul a iesit
      // explicit din cont, il lasam afara — altfel butonul de logout n-ar face nimic.
      if (DEMO_MODE && !hasOptedOut()) {
        try {
          await loginAsDemo('user')
          return
        } catch {
          /* daca API-ul nu raspunde, cadem pe starea normala de nelogat */
        }
      }
      setUser(null)
      setStatus('anonymous')
      return
    }
    try {
      const { data } = await api.get<AuthUser>('/auth/me')
      setUser(data)
      setStatus('authenticated')
    } catch {
      setToken(null)
      setUser(null)
      setStatus('anonymous')
    }
  }, [loginAsDemo])

  // Sesiune expirata semnalata de interceptor.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      setStatus('anonymous')
      toast.info('Sesiunea a expirat. Intră din nou.')
      navigate('/login')
    })
    return () => setUnauthorizedHandler(null)
  }, [navigate, toast])

  useEffect(() => {
    if (bootstrapped.current) return
    bootstrapped.current = true
    void refresh()
  }, [refresh])

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await api.post<TokenResponse>('/auth/login', { email, password })
      setOptedOut(false)
      applyToken(data)
    },
    [applyToken],
  )

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const { data } = await api.post<TokenResponse>('/auth/register', {
        email,
        password,
        display_name: displayName || undefined,
      })
      applyToken(data)
    },
    [applyToken],
  )

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      /* logout e best-effort: chiar daca serverul nu raspunde, iesim local */
    }
    setToken(null)
    setUser(null)
    setStatus('anonymous')
    setOptedOut(true) // in demo: nu ne mai logam automat la loc
    navigate('/')
  }, [navigate])

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, register, logout, refresh, loginAsDemo }),
    [user, status, login, register, logout, refresh, loginAsDemo],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth trebuie folosit in interiorul <AuthProvider>')
  return ctx
}
