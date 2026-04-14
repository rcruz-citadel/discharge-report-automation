import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from './useAuth'

interface RequireAuthProps {
  children: ReactNode
}

/**
 * Route guard: redirects unauthenticated users to /login.
 * Shows nothing while auth state is loading (avoids flash of login page).
 */
export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-page flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-navy border-t-orange rounded-full animate-spin" />
          <p className="text-text-secondary text-sm">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
