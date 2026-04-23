export interface DischargeRecord {
  event_id: string
  discharge_date: string          // ISO date string "YYYY-MM-DD"
  patient_name: string | null
  insurance_member_id: string | null
  practice: string | null
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
}

export type OutreachStatus = 'no_outreach' | 'outreach_made' | 'outreach_complete' | 'failed'

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
}

export interface OutreachUpsertPayload {
  event_id: string
  discharge_date: string
  status: OutreachStatus
  notes: string
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
}

export const OUTREACH_STATUS_LABELS: Record<OutreachStatus, string> = {
  no_outreach: 'No Outreach',
  outreach_made: 'Outreach Made',
  outreach_complete: 'Outreach Complete',
  failed: 'Failed',
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
}
