import { useEffect, useState } from 'react'
import { cn } from '../../lib/utils'

type ToastVariant = 'success' | 'error'

interface ToastProps {
  message: string
  variant?: ToastVariant
  onDismiss: () => void
  duration?: number
}

/**
 * Auto-dismissing toast notification. Fixed top-right.
 * Success: green. Error: red. Spec: 5.8 Loading and Empty States
 */
export function Toast({ message, variant = 'success', onDismiss, duration = 3000 }: ToastProps) {
  const [exiting, setExiting] = useState(false)

  useEffect(() => {
    const exitTimer = setTimeout(() => setExiting(true), duration)
    const dismissTimer = setTimeout(onDismiss, duration + 200)
    return () => {
      clearTimeout(exitTimer)
      clearTimeout(dismissTimer)
    }
  }, [duration, onDismiss])

  const isSuccess = variant === 'success'

  return (
    <div
      className={cn(
        'fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-panel border text-[13px] font-medium max-w-sm',
        exiting ? 'toast-exit' : 'toast-enter'
      )}
      style={
        isSuccess
          ? { backgroundColor: '#f0fff4', borderColor: '#9ae6b4', color: '#22543d' }
          : { backgroundColor: '#fee2e2', borderColor: '#fca5a5', color: '#991b1b' }
      }
      role={isSuccess ? 'status' : 'alert'}
      aria-live={isSuccess ? 'polite' : 'assertive'}
    >
      {isSuccess ? (
        <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      ) : (
        <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      )}
      <span>{message}</span>
      <button
        onClick={() => { setExiting(true); setTimeout(onDismiss, 200) }}
        className="ml-auto text-current opacity-60 hover:opacity-100 transition-opacity"
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  )
}

// ── Toast state hook ──────────────────────────────────────────────────────────

interface ToastState {
  id: number
  message: string
  variant: ToastVariant
}

let toastIdCounter = 0

export function useToast() {
  const [toasts, setToasts] = useState<ToastState[]>([])

  const show = (message: string, variant: ToastVariant = 'success') => {
    const id = ++toastIdCounter
    setToasts(prev => [...prev, { id, message, variant }])
  }

  const dismiss = (id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  const ToastContainer = () => (
    <>
      {toasts.map(t => (
        <Toast key={t.id} message={t.message} variant={t.variant} onDismiss={() => dismiss(t.id)} />
      ))}
    </>
  )

  return { show, ToastContainer }
}
