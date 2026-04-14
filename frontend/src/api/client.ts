import axios from 'axios'

/**
 * Axios instance configured for the discharge report API.
 *
 * withCredentials: true — sends the httpOnly session cookie on every request.
 * No Authorization header. No token in localStorage. The cookie does the work.
 *
 * 401 interceptor: redirect to /login for any unauthenticated response.
 */
export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Clear any stale client-side state and redirect to login
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
