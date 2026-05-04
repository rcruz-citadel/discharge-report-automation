export interface DischargeRecord {
  event_id: string
  discharge_date: string          // ISO date string "YYYY-MM-DD"
  patient_name: string | null
  insurance_member_id: string | null
  birth_date: string | null        // ISO date string "YYYY-MM-DD"
  phone: string | null
  practice: string | null
  provider_name: string | null
  payer_name: string | null
  lob_name: string | null
  stay_type: string | null
  discharge_hospital: string | null
  length_of_stay: number | null
  disposition: string | null
  dx_code: string | null
  description: string | null
  admit_date: string | null       // ISO date string "YYYY-MM-DD"
  outreach_status: OutreachStatus
  outreach_notes: string
  outreach_updated_by: string | null
  outreach_updated_at: string | null  // ISO datetime string
  discharge_summary_dropped: boolean
  failure_reason: 'missed_48h' | 'missed_tcm_window' | null
  original_failure_reason: 'missed_48h' | 'missed_tcm_window' | 'late_delivery' | null
}

export type OutreachStatus =
  | 'no_outreach'
  | 'outreach_made'
  | 'outreach_complete'
  | 'failed'
  | 'late_delivery'
  | 'no_outreach_required'

export interface DischargesResponse {
  records: DischargeRecord[]
  total: number
  loaded_at: string
}

export interface OutreachRecord {
  event_id: string
  discharge_date: string
  status: OutreachStatus
  notes: string
  updated_by: string | null
  updated_at: string | null
  discharge_summary_dropped: boolean
}

export interface OutreachUpsertPayload {
  event_id: string
  discharge_date: string
  status: OutreachStatus
  notes: string
  discharge_summary_dropped: boolean
}

export interface OutreachAttempt {
  id: number
  event_id: string
  discharge_date: string
  attempt_number: number
  attempted_by: string
  attempted_at: string  // ISO datetime string
}

export interface LogAttemptResponse {
  attempt: OutreachAttempt
  attempt_number: number
  attempts_remaining: number
  auto_completed: boolean
}

export const OUTREACH_STATUS_LABELS: Record<OutreachStatus, string> = {
  no_outreach: 'No Outreach',
  outreach_made: 'Outreach Made',
  outreach_complete: 'Outreach Complete',
  failed: 'Failed',
  late_delivery: 'Late Delivery',
  no_outreach_required: 'No Outreach Needed',
}

export const OUTREACH_STATUS_COLORS: Record<OutreachStatus, {
  dot: string
  pillBg: string
  pillText: string
  rowTint: string
  btnBg: string
  btnBorder: string
  btnText: string
}> = {
  no_outreach: {
    dot: '#cbd5e0',
    pillBg: '#edf2f7',
    pillText: '#718096',
    rowTint: 'transparent',
    btnBg: '#edf2f7',
    btnBorder: '#a0aec0',
    btnText: '#718096',
  },
  outreach_made: {
    dot: '#e07b2a',
    pillBg: '#fef3e2',
    pillText: '#c05621',
    rowTint: 'rgba(224,123,42,0.04)',
    btnBg: '#fff3e0',
    btnBorder: '#e07b2a',
    btnText: '#c05621',
  },
  outreach_complete: {
    dot: '#38a169',
    pillBg: '#e6ffed',
    pillText: '#22753a',
    rowTint: 'rgba(56,161,105,0.04)',
    btnBg: '#e6ffed',
    btnBorder: '#38a169',
    btnText: '#22753a',
  },
  failed: {
    dot: '#e53e3e',
    pillBg: '#fed7d7',
    pillText: '#c53030',
    rowTint: 'rgba(229,62,62,0.04)',
    btnBg: '#fed7d7',
    btnBorder: '#e53e3e',
    btnText: '#c53030',
  },
  late_delivery: {
    dot: '#4299e1',
    pillBg: '#ebf8ff',
    pillText: '#2b6cb0',
    rowTint: 'rgba(66,153,225,0.04)',
    btnBg: '#ebf8ff',
    btnBorder: '#90cdf4',
    btnText: '#2b6cb0',
  },
  no_outreach_required: {
    dot: '#9f7aea',
    pillBg: '#faf5ff',
    pillText: '#6b46c1',
    rowTint: 'transparent',
    btnBg: '#faf5ff',
    btnBorder: '#d6bcfa',
    btnText: '#6b46c1',
  },
}

/** Days remaining in TCM window. ER = 7d, all others = 30d. Negative = past deadline. */
export function getDaysRemaining(row: DischargeRecord): number {
  const discharge = new Date(row.discharge_date + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const ageDays = Math.floor((today.getTime() - discharge.getTime()) / (1000 * 60 * 60 * 24))
  const deadline = row.stay_type?.toLowerCase().includes('emergency') ? 7 : 30
  return deadline - ageDays
}

/** Queue bucket a record belongs to based on its discharge age vs TCM window. */
export type QueueBucket = 'immediate' | 'active' | 'low_priority' | 'resolved'

/** Statuses that route a record to the Resolved tab regardless of age. */
export const RESOLVED_STATUSES: ReadonlySet<OutreachStatus> = new Set([
  'outreach_complete',
  'no_outreach_required',
])

export function getQueueBucket(row: DischargeRecord): QueueBucket {
  if (RESOLVED_STATUSES.has(row.outreach_status)) return 'resolved'
  const discharge = new Date(row.discharge_date + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const ageDays = Math.floor((today.getTime() - discharge.getTime()) / (1000 * 60 * 60 * 24))
  if (ageDays <= 2) return 'immediate'
  const deadline = row.stay_type?.toLowerCase().includes('emergency') ? 7 : 30
  if (ageDays < deadline) return 'active'
  return 'low_priority'
}
