import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import type { User } from '../types/auth'

export interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  isManager: boolean
  refetch: () => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

interface AuthProviderProps {
  children: ReactNode
}

/**
 * AuthProvider checks the session cookie on mount by calling GET /api/auth/me.
 *
 * - If the call returns 200: user is authenticated, store user in context.
 * - If the call returns 401: no valid session. The axios interceptor in api/client.ts
 *   will redirect to /login, but we also set user=null here for cleanliness.
 *
 * The 401 redirect in the interceptor handles unauthenticated navigation globally.
 * We suppress the redirect for the initial /me check (isLoading=true phase) to
 * avoid a redirect loop on the /login page itself.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const fetchUser = useCallback(async () => {
    try {
      const response = await api.get<User>('/auth/me')
      setUser(response.data)
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // Ignore errors — cookie will expire anyway
    }
    setUser(null)
    window.location.href = '/login'
  }, [])

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    isManager: user?.role === 'manager' || user?.role === 'admin',
    refetch: fetchUser,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
