import { cn } from '../../lib/utils'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeMap = {
  sm: 'w-4 h-4 border-2',
  md: 'w-6 h-6 border-2',
  lg: 'w-8 h-8 border-2',
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  return (
    <div
      className={cn(
        'rounded-full border-navy border-t-orange animate-spin',
        sizeMap[size],
        className
      )}
      role="status"
      aria-label="Loading"
    />
  )
}
