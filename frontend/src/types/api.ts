import type { OutreachStatus } from '../types/discharge'

export interface AssigneeInfo {
  name: string
  practices: string[]
}

export interface MetaFiltersResponse {
  practices: string[]
  payers: string[]
  lob_names: string[]
  stay_types: string[]
  assignees: AssigneeInfo[]
  discharge_date_min: string | null
  discharge_date_max: string | null
}

export interface OutreachSummary {
  total: number
  no_outreach: number
  outreach_made: number
  outreach_complete: number
  pct_complete: number
}

export interface StaffBreakdownRow {
  user_email: string
  display_name: string
  practice_count: number
  total: number
  no_outreach: number
  outreach_made: number
  outreach_complete: number
  pct_complete: number
  last_login: string | null
  last_activity: string | null
}

export interface PracticeRollupRow {
  practice: string
  total: number
  no_outreach: number
  outreach_made: number
  outreach_complete: number
  pct_complete: number
}

export interface ManagerMetricsResponse {
  summary: OutreachSummary
  staff_breakdown: StaffBreakdownRow[]
  practice_rollup: PracticeRollupRow[]
}

export interface FilterState {
  assignee: string
  practices: string[]
  payers: string[]
  lobNames: string[]
  stayTypes: string[]
  dateFrom: string | null
  dateTo: string | null
  outreachStatuses: OutreachStatus[]
}
