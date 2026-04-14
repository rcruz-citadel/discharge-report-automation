import type { Configuration } from '@azure/msal-browser'

export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AUTH_CLIENT_ID ?? '',
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AUTH_TENANT_ID ?? 'common'}`,
    redirectUri: `${window.location.origin}/auth/callback`,
    postLogoutRedirectUri: `${window.location.origin}/login`,
  },
  cache: {
    // sessionStorage only: MSAL stores PKCE code verifier/state here.
    // Access tokens never live in the browser — the backend issues httpOnly session cookies.
    cacheLocation: 'sessionStorage',
  },
}

export const loginRequest = {
  scopes: ['openid', 'profile', 'email'],
}
