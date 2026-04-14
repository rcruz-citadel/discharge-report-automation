import type { ColumnDef } from '@tanstack/react-table'
import type { DischargeRecord } from '../../types/discharge'
import { StatusPill } from '../ui/StatusPill'
import { formatDate, orDash } from '../../lib/utils'

/**
 * TanStack Table column definitions for the discharge table.
 * Spec: 5.5 Discharge Table columns
 */
export const dischargeColumns: ColumnDef<DischargeRecord>[] = [
  {
    accessorKey: 'patient_name',
    header: 'Patient Name',
    size: 180,
    cell: ({ getValue }) => (
      <span className="font-medium">{orDash(getValue<string | null>())}</span>
    ),
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
    accessorKey: 'payer_name',
    header: 'Payer',
    size: 150,
    cell: ({ getValue }) => orDash(getValue<string | null>()),
  },
  {
    accessorKey: 'discharge_hospital',
    header: 'Hospital',
    size: 180,
    cell: ({ getValue }) => orDash(getValue<string | null>()),
  },
  {
    accessorKey: 'length_of_stay',
    header: 'LOS',
    size: 80,
    meta: { align: 'right' },
    cell: ({ getValue }) => {
      const val = getValue<number | null>()
      return val != null ? String(val) : '—'
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
    header: 'Status',
    size: 160,
    cell: ({ row }) => (
      <StatusPill status={row.original.outreach_status} />
    ),
  },
]
