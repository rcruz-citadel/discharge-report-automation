import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { PublicClientApplication } from '@azure/msal-browser'
import { msalConfig } from '../auth/msalConfig'
import { api } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

/**
 * OAuth callback page. Handles the redirect from Microsoft after login.
 *
 * Flow:
 * 1. Microsoft redirects to /auth/callback?code=...
 * 2. MSAL handles the redirect (extracts code, validates state)
 * 3. We POST the code to /api/auth/callback to exchange for a server-side session
 * 4. Backend sets httpOnly session cookie and returns { ok: true }
 * 5. We navigate to / — AuthProvider re-checks /api/auth/me with the new cookie
 *
 * Spec: 3.4 Full Auth Flow steps 8-16
 */
export function CallbackPage() {
  const navigate = useNavigate()
  const { refetch } = useAuth()
  const hasHandled = useRef(false)

  useEffect(() => {
    if (hasHandled.current) return
    hasHandled.current = true

    async function handleCallback() {
      try {
        const msalInstance = new PublicClientApplication(msalConfig)
        await msalInstance.initialize()

        // Let MSAL process the redirect (validates state, extracts code)
        const result = await msalInstance.handleRedirectPromise()

        if (!result) {
          // No redirect response — user navigated directly to /auth/callback
          navigate('/login', { replace: true })
          return
        }

        // Exchange the code for a server-side session cookie
        const redirectUri = `${window.location.origin}/auth/callback`
        await api.post('/auth/callback', {
          code: result.code ?? (new URLSearchParams(window.location.search).get('code') ?? ''),
          redirect_uri: redirectUri,
        })

        // Refresh auth context — the new httpOnly cookie is now set
        await refetch()

        navigate('/', { replace: true })
      } catch (err) {
        console.error('Auth callback failed:', err)
        navigate('/login?error=auth_failed', { replace: true })
      }
    }

    handleCallback()
  }, [navigate, refetch])

  return (
    <div className="min-h-screen bg-page flex flex-col items-center justify-center gap-3">
      <LoadingSpinner size="lg" />
      <p className="text-text-secondary text-sm">Completing sign in...</p>
    </div>
  )
}
