import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PublicClientApplication } from '@azure/msal-browser'
import { msalConfig, loginRequest } from '../auth/msalConfig'
import { useAuth } from '../auth/useAuth'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

/**
 * Login page with branded card, sign in button, domain restriction notice.
 * Spec: 5.5 Login Page
 */
export function LoginPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()

  // Already authenticated: redirect to dashboard
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate])

  const handleSignIn = async () => {
    const msalInstance = new PublicClientApplication(msalConfig)
    await msalInstance.initialize()
    await msalInstance.loginRedirect(loginRequest)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-page flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-page flex flex-col items-center" style={{ paddingTop: '80px' }}>
      {/* Max-width column */}
      <div className="w-full max-w-[420px] px-4">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <img
            src="/citadel-logo-hd-transparent.png"
            alt="Citadel Health"
            className="w-40 object-contain"
          />
        </div>

        {/* Login card */}
        <div
          className="relative rounded-[16px] p-8 overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, #132e45 0%, #1b4459 100%)',
            boxShadow: '0 6px 28px rgba(19,46,69,0.22)',
          }}
        >
          {/* Right orange accent */}
          <div
            className="absolute right-0 top-0 bottom-0 w-[5px] rounded-r-[16px]"
            style={{ background: 'linear-gradient(180deg, #e07b2a 0%, #c96920 100%)' }}
            aria-hidden="true"
          />

          <h1
            className="text-[21.6px] font-extrabold text-white mb-1"
          >
            Discharge Report Dashboard
          </h1>
          <p className="text-[14px] text-[#a8c4d8] mb-8">
            Sign in to access outreach tracking
          </p>

          <button
            onClick={handleSignIn}
            className="w-full py-3 rounded-[9px] text-[15.2px] font-bold text-white transition-colors duration-200"
            style={{
              backgroundColor: '#e07b2a',
              boxShadow: '0 2px 8px rgba(224,123,42,0.35)',
            }}
            onMouseEnter={e => {
              ;(e.currentTarget as HTMLButtonElement).style.backgroundColor = '#c96920'
            }}
            onMouseLeave={e => {
              ;(e.currentTarget as HTMLButtonElement).style.backgroundColor = '#e07b2a'
            }}
          >
            Sign in with Microsoft
          </button>

          <p className="mt-4 text-[12px] text-center" style={{ color: '#7e96a6' }}>
            Access restricted to: @citadelhealth.com, @aylohealth.com
          </p>
        </div>
      </div>
    </div>
  )
}
