import type { OutreachStatus } from '../../types/discharge'
import { OUTREACH_STATUS_COLORS, OUTREACH_STATUS_LABELS } from '../../types/discharge'
import { cn } from '../../lib/utils'

interface StatusPillProps {
  status: OutreachStatus
  className?: string
}

/**
 * Inline pill badge showing outreach status with colored dot.
 * Used in the discharge table Status column.
 */
export function StatusPill({ status, className }: StatusPillProps) {
  const colors = OUTREACH_STATUS_COLORS[status]
  const label = OUTREACH_STATUS_LABELS[status]

  return (
    <span
      className={cn('inline-flex items-center gap-[5px] px-[10px] py-[3px] rounded-full text-[11.8px] font-semibold', className)}
      style={{
        backgroundColor: colors.pillBg,
        color: colors.pillText,
      }}
    >
      <span
        className="w-[7px] h-[7px] rounded-full shrink-0"
        style={{ backgroundColor: colors.dot }}
        aria-hidden="true"
      />
      {label}
    </span>
  )
}
