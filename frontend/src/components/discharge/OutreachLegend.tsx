import { OUTREACH_STATUS_COLORS, OUTREACH_STATUS_LABELS } from '../../types/discharge'
import type { OutreachStatus } from '../../types/discharge'

const statuses: OutreachStatus[] = ['no_outreach', 'outreach_made', 'outreach_complete']

export function OutreachLegend() {
  return (
    <div className="flex items-center gap-6 flex-wrap" aria-label="Outreach status legend">
      {statuses.map(status => (
        <span key={status} className="inline-flex items-center gap-2 text-[12.5px] text-text-secondary">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: OUTREACH_STATUS_COLORS[status].dot }}
            aria-hidden="true"
          />
          {OUTREACH_STATUS_LABELS[status]}
        </span>
      ))}
    </div>
  )
}
