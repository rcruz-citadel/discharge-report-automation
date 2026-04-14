import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth } from './auth/RequireAuth'
import { LoginPage } from './pages/LoginPage'
import { CallbackPage } from './pages/CallbackPage'
import { DashboardPage } from './pages/DashboardPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

/**
 * Root application component.
 *
 * Tree:
 *   BrowserRouter
 *   └── QueryClientProvider
 *       └── AuthProvider (session cookie check via /api/auth/me)
 *           ├── /login         -> LoginPage
 *           ├── /auth/callback -> CallbackPage
 *           └── /              -> RequireAuth -> DashboardPage
 *
 * MSAL.js is only instantiated on demand (LoginPage, CallbackPage) — not wrapped
 * around the whole app — because auth state comes from the server-side session
 * cookie (/api/auth/me), not MSAL token cache.
 */
export default function App() {
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/auth/callback" element={<CallbackPage />} />
            <Route
              path="/"
              element={
                <RequireAuth>
                  <DashboardPage />
                </RequireAuth>
              }
            />
            {/* Catch-all redirect to dashboard */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}
