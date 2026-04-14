import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cn } from '../../lib/utils'
import { LoadingSpinner } from './LoadingSpinner'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  isLoading?: boolean
  children: ReactNode
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-orange text-white font-bold hover:bg-orange-hover shadow-btn-cta transition-colors duration-200',
  secondary:
    'bg-transparent border border-[1.5px] border-border text-text-secondary hover:border-navy hover:text-navy transition-colors duration-200',
  ghost:
    'bg-transparent text-text-secondary hover:bg-navy/5 transition-colors duration-200',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', isLoading, children, className, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        aria-busy={isLoading}
        className={cn(
          'inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-semibold',
          'focus-visible:outline-2 focus-visible:outline-orange focus-visible:outline-offset-2',
          'disabled:opacity-60 disabled:cursor-not-allowed',
          variantStyles[variant],
          className
        )}
        {...props}
      >
        {isLoading ? <LoadingSpinner size="sm" /> : children}
      </button>
    )
  }
)

Button.displayName = 'Button'
