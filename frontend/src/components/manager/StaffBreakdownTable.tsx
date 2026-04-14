import type { StaffBreakdownRow } from '../../types/api'
import { formatDate } from '../../lib/utils'

interface StaffBreakdownTableProps {
  rows: StaffBreakdownRow[]
}

/**
 * Staff breakdown table for manager dashboard.
 * Spec: 5.5 Manager Dashboard, Staff Breakdown columns
 */
export function StaffBreakdownTable({ rows }: StaffBreakdownTableProps) {
  return (
    <div className="bg-surface rounded-lg shadow-card overflow-hidden">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {[
              ['Name', '160px'],
              ['Practices', '80px'],
              ['Total', '80px'],
              ['No Outreach', '100px'],
              ['Made', '80px'],
              ['Complete', '80px'],
              ['% Done', '80px'],
              ['Last Login', '100px'],
              ['Last Activity', '100px'],
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
            <tr
              key={row.user_email}
              className="border-b border-border-light hover:bg-[#f7f9fb] transition-colors"
            >
              <td className="px-3 py-[9px] text-[13px] font-medium text-text-primary">{row.display_name}</td>
              <td className="px-3 py-[9px] text-[13px] text-center text-text-primary">{row.practice_count}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-primary">{row.total.toLocaleString()}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-primary">{row.no_outreach.toLocaleString()}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-primary">{row.outreach_made.toLocaleString()}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-primary">{row.outreach_complete.toLocaleString()}</td>
              <td className="px-3 py-[9px] text-[13px] font-bold text-text-primary">{row.pct_complete}%</td>
              <td className="px-3 py-[9px] text-[13px] text-text-secondary">{formatDate(row.last_login)}</td>
              <td className="px-3 py-[9px] text-[13px] text-text-secondary">{formatDate(row.last_activity)}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={9} className="px-3 py-8 text-center text-[13px] text-text-muted">
                No staff data available.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
