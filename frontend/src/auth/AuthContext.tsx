import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import type { ReactNode } from 'react'
import type { LoginCredentials, User } from '../types'
import {
  authFetch,
  clearTokens,
  getTokens,
  setTokens,
} from './authFetch'

interface AuthState {
  user: User | null
  loading: boolean
  login: (creds: LoginCredentials) => Promise<string | null>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMe = useCallback(async () => {
    const tokens = getTokens()
    if (!tokens) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const resp = await authFetch('/auth/me')
      if (resp.ok) {
        const data = await resp.json()
        setUser(data)
      } else {
        clearTokens()
        setUser(null)
      }
    } catch {
      clearTokens()
      setUser(null)
    }

    setLoading(false)
  }, [])

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  const login = useCallback(async (creds: LoginCredentials): Promise<string | null> => {
    try {
      const resp = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(creds),
      })

      if (!resp.ok) {
        const body = await resp.json().catch(() => null)
        return body?.detail ?? 'Credenciais invalidas.'
      }

      const tokens = await resp.json()
      setTokens(tokens)

      const meResp = await authFetch('/auth/me')
      if (meResp.ok) {
        setUser(await meResp.json())
      }

      return null
    } catch {
      return 'Erro de conexao com o servidor.'
    }
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
