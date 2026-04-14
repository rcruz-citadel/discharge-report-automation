import { StatChip } from '../ui/StatChip'
import { StaffBreakdownTable } from './StaffBreakdownTable'
import { PracticeRollupTable } from './PracticeRollupTable'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { useManagerMetrics } from '../../hooks/useManagerMetrics'
import { Button } from '../ui/Button'

/**
 * Manager dashboard tab content.
 * Shows 5 summary chips, staff breakdown table, and practice roll-up table.
 * Role-gated: only rendered for managers (enforced in DashboardPage).
 * Spec: 5.5 Manager Dashboard
 */
export function ManagerDashboard() {
  const { data, isLoading, isError, refetch } = useManagerMetrics()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex flex-col items-center gap-3 py-16">
        <svg className="w-12 h-12 text-orange" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
        <p className="text-[16px] font-bold text-text-primary">Could not load manager metrics</p>
        <Button variant="secondary" onClick={() => refetch()}>Retry</Button>
      </div>
    )
  }

  const { summary, staff_breakdown, practice_rollup } = data

  return (
    <div className="flex flex-col gap-6">
      {/* Summary stat chips */}
      <div className="flex gap-3 flex-wrap">
        <StatChip label="Total Discharges" value={summary.total.toLocaleString()} variant="navy" />
        <StatChip label="No Outreach" value={summary.no_outreach.toLocaleString()} variant="gray" />
        <StatChip label="Outreach Made" value={summary.outreach_made.toLocaleString()} variant="orange" />
        <StatChip label="Complete" value={summary.outreach_complete.toLocaleString()} variant="green" />
        <StatChip label="% Complete" value={`${summary.pct_complete}%`} variant="green" />
      </div>

      {/* Staff breakdown */}
      <div>
        <h2 className="text-[16px] font-bold text-text-primary mb-3">Staff Breakdown</h2>
        <StaffBreakdownTable rows={staff_breakdown} />
      </div>

      {/* Practice roll-up */}
      <div>
        <h2 className="text-[16px] font-bold text-text-primary mb-3">Practice Roll-Up</h2>
        <PracticeRollupTable rows={practice_rollup} />
      </div>
    </div>
  )
}
