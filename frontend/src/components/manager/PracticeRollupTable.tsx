import type { PracticeRollupRow } from '../../types/api'

interface PracticeRollupTableProps {
  rows: PracticeRollupRow[]
}

/**
 * Practice roll-up table for manager dashboard.
 * Sorted by Total DESC (server-side). Spec: 5.5 Manager Dashboard
 */
export function PracticeRollupTable({ rows }: PracticeRollupTableProps) {
  return (
    <div className="bg-surface rounded-lg shadow-card overflow-hidden">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {[
              ['Practice', '200px'],
              ['Total', '80px'],
              ['No Outreach', '100px'],
              ['Made', '80px'],
              ['Complete', '80px'],
              ['% Done', '80px'],
            ].map(([label, width]) => (
              <th
                key={label}
                className="bg-navy text-white text-[12px] font-semibold uppercase px-3 py-[10px] text-left whitespace-nowrap"
                style={{ width }}
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.practice} className="border-b border-border-light hover:bg-[#f7f9fb] transition-colors">
              <td className="px-3 py-[9px] text-[13px] font-medium text-text-primary">{row.practice}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-primary">{row.total.toLocaleString()}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-primary">{row.no_outreach.toLocaleString()}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-primary">{row.outreach_made.toLocaleString()}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-primary">{row.outreach_complete.toLocaleString()}</td>
              <td className="px-3 py-[9px] text-[13px] font-bold text-text-primary">{row.pct_complete}%</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-[13px] text-text-muted">
                No practice data available.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
