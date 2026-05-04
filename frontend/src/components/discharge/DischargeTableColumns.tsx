import type { ColumnDef } from '@tanstack/react-table'
import type { DischargeRecord } from '../../types/discharge'
import { getDaysRemaining, getQueueBucket } from '../../types/discharge'
import { StatusPill } from '../ui/StatusPill'
import { formatDate, orDash } from '../../lib/utils'

function DaysLeftBadge({ row }: { row: DischargeRecord }) {
  const bucket = getQueueBucket(row)
  if (bucket === 'low_priority' || bucket === 'resolved') {
    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold"
        style={{ backgroundColor: '#edf2f7', color: '#718096' }}
      >
        —
      </span>
    )
  }

  const days = getDaysRemaining(row)

  let bg: string
  let color: string
  let label: string

  if (days <= 0) {
    bg = '#feebc8'; color = '#c05621'; label = 'Overdue'
  } else if (days === 1) {
    bg = '#feebc8'; color = '#c05621'; label = '1d left'
  } else if (days <= 3) {
    bg = '#fefcbf'; color = '#975a16'; label = `${days}d left`
  } else {
    bg = '#e6ffed'; color = '#22753a'; label = `${days}d left`
  }

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
      style={{ backgroundColor: bg, color }}
    >
      {label}
    </span>
  )
}

export const dischargeColumns: ColumnDef<DischargeRecord>[] = [
  {
    id: 'days_left',
    header: 'Deadline',
    size: 90,
    cell: ({ row }) => <DaysLeftBadge row={row.original} />,
    sortingFn: (a, b) => getDaysRemaining(a.original) - getDaysRemaining(b.original),
  },
  {
    accessorKey: 'patient_name',
    header: 'Patient Name',
    size: 180,
    cell: ({ getValue }) => (
      <span className="font-medium">{orDash(getValue<string | null>())}</span>
    ),
  },
  {
    accessorKey: 'admit_date',
    header: 'Admit Date',
    size: 110,
    cell: ({ getValue }) => formatDate(getValue<string | null>()),
    sortingFn: 'alphanumeric',
  },
  {
    accessorKey: 'discharge_date',
    header: 'Discharge Date',
    size: 120,
    cell: ({ getValue }) => formatDate(getValue<string | null>()),
    sortingFn: 'alphanumeric',
  },
  {
    accessorKey: 'practice',
    header: 'Practice',
    size: 160,
    cell: ({ getValue }) => orDash(getValue<string | null>()),
  },
  {
    accessorKey: 'provider_name',
    header: 'Provider',
    size: 150,
    cell: ({ getValue }) => orDash(getValue<string | null>()),
  },
  {
    accessorKey: 'payer_name',
    header: 'Payer',
    size: 150,
    cell: ({ getValue }) => orDash(getValue<string | null>()),
  },
  {
    accessorKey: 'discharge_hospital',
    header: 'Hospital',
    size: 180,
    cell: ({ getValue }) => {
      const val = getValue<string | null>()
      if (!val) {
        return (
          <span
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold"
            style={{ backgroundColor: '#fefcbf', color: '#975a16' }}
            title="Hospital unknown — check payer portal"
          >
            ⚠ Unknown
          </span>
        )
      }
      return val
    },
  },
  {
    accessorKey: 'length_of_stay',
    header: 'LOS',
    size: 70,
    meta: { align: 'right' },
    cell: ({ getValue }) => {
      const val = getValue<number | null>()
      return val != null ? String(val) : '—'
    },
  },
  {
    accessorKey: 'description',
    header: 'Diagnosis',
    size: 180,
    cell: ({ row }) => {
      const code = row.original.dx_code
      const desc = row.original.description
      return orDash(code && desc ? `${code} — ${desc}` : desc ?? code)
    },
  },
  {
    accessorKey: 'disposition',
    header: 'Disposition',
    size: 130,
    cell: ({ getValue }) => orDash(getValue<string | null>()),
  },
  {
    accessorKey: 'outreach_status',
    header: 'Outreach',
    size: 160,
    cell: ({ row }) => {
      const { outreach_status, failure_reason, original_failure_reason } = row.original

      // Translate system statuses to coordinator-friendly pill
      let pillStatus = outreach_status
      if (outreach_status === 'failed' && failure_reason === 'missed_48h') {
        pillStatus = 'no_outreach'
      } else if (outreach_status === 'late_delivery') {
        const bucket = getQueueBucket(row.original)
        pillStatus = bucket === 'low_priority' ? 'failed' : 'no_outreach'
      }

      // Context badge: driven by original_failure_reason (persists after status changes)
      // Falls back to current status/failure_reason for pre-backfill records
      const showMissed48h = original_failure_reason === 'missed_48h' ||
        (outreach_status === 'failed' && failure_reason === 'missed_48h')
      const showLateAdt = original_failure_reason === 'late_delivery' ||
        outreach_status === 'late_delivery'

      if (showMissed48h || showLateAdt) {
        return (
          <span className="inline-flex items-center gap-2">
            <StatusPill status={pillStatus} />
            <span
              className="inline-flex items-center gap-1"
              style={{ fontSize: 10, fontWeight: 500, color: showMissed48h ? '#975a16' : '#3b82f6' }}
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: showMissed48h ? '#d69e2e' : '#93c5fd', flexShrink: 0, display: 'inline-block' }} />
              {showMissed48h ? '48h Missed' : 'Late ADT'}
            </span>
          </span>
        )
      }

      return <StatusPill status={outreach_status} />
    },
  },
]
