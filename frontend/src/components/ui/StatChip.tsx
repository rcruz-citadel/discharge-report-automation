import { cn } from '../../lib/utils'

type StatChipVariant = 'navy' | 'orange' | 'green' | 'gray'

interface StatChipProps {
  label: string
  value: string | number
  variant?: StatChipVariant
  className?: string
}

const variantStyles: Record<StatChipVariant, { border: string; value: string }> = {
  navy: { border: '#132e45', value: '#132e45' },
  orange: { border: '#e07b2a', value: '#e07b2a' },
  green: { border: '#38a169', value: '#22753a' },
  gray: { border: '#a0aec0', value: '#718096' },
}

/**
 * Stat chip with 4px left border, label, and large value.
 * Used in StatChipRow for summary statistics.
 */
export function StatChip({ label, value, variant = 'navy', className }: StatChipProps) {
  const styles = variantStyles[variant]

  return (
    <div
      className={cn(
        'bg-surface border border-border rounded-lg px-[18px] py-[10px] shadow-chip',
        'border-l-[4px] flex flex-col gap-0.5',
        className
      )}
      style={{ borderLeftColor: styles.border }}
    >
      <span
        className="text-[11.5px] font-bold uppercase tracking-wider"
        style={{ color: '#556e81' }}
      >
        {label}
      </span>
      <span
        className="text-[24.8px] font-extrabold leading-tight"
        style={{ color: styles.value }}
      >
        {value}
      </span>
    </div>
  )
}
