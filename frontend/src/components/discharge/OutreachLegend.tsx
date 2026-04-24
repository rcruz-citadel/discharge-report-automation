import { OUTREACH_STATUS_COLORS, OUTREACH_STATUS_LABELS } from '../../types/discharge'
import type { OutreachStatus } from '../../types/discharge'

const ALL_STATUSES: OutreachStatus[] = ['no_outreach', 'outreach_made', 'outreach_complete', 'failed']

interface OutreachLegendProps {
  activeStatuses: OutreachStatus[]
  onToggle: (status: OutreachStatus) => void
}

export function OutreachLegend({ activeStatuses, onToggle }: OutreachLegendProps) {
  return (
    <div
      className="flex items-center gap-2 flex-wrap"
      role="group"
      aria-label="Filter by outreach status"
    >
      <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider mr-1">
        Filter:
      </span>
      {ALL_STATUSES.map(status => {
        const isActive = activeStatuses.includes(status)
        const colors = OUTREACH_STATUS_COLORS[status]

        return (
          <button
            key={status}
            type="button"
            aria-pressed={isActive}
            onClick={() => onToggle(status)}
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-semibold cursor-pointer hover:opacity-80 transition-opacity"
            style={
              isActive
                ? {
                    background: colors.pillBg,
                    color: colors.pillText,
                    border: `1.5px solid ${colors.btnBorder}`,
                  }
                : {
                    background: '#f7f9fb',
                    color: '#718096',
                    border: '1.5px solid #d0dae3',
                  }
            }
          >
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: colors.dot }}
              aria-hidden="true"
            />
            {OUTREACH_STATUS_LABELS[status]}
          </button>
        )
      })}
    </div>
  )
}
