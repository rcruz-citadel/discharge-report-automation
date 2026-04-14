import { StatChip } from './StatChip'
import type { OutreachStatus } from '../../types/discharge'

interface StatChipRowProps {
  records: Array<{ outreach_status: OutreachStatus; practice: string | null; discharge_hospital: string | null; patient_name: string | null }>
}

/**
 * Row of 4 stat chips: Total Records, Unique Patients, Practices, Hospitals.
 * Mirrors the V2 Streamlit stat chips (lines 1063-1073).
 */
export function StatChipRow({ records }: StatChipRowProps) {
  const total = records.length
  const uniquePatients = new Set(records.map(r => r.patient_name).filter(Boolean)).size
  const uniquePractices = new Set(records.map(r => r.practice).filter(Boolean)).size
  const uniqueHospitals = new Set(records.map(r => r.discharge_hospital).filter(Boolean)).size

  return (
    <div className="flex gap-3 flex-wrap">
      <StatChip label="Total Records" value={total.toLocaleString()} variant="navy" />
      <StatChip label="Unique Patients" value={uniquePatients.toLocaleString()} variant="navy" />
      <StatChip label="Practices" value={uniquePractices.toLocaleString()} variant="orange" />
      <StatChip label="Hospitals" value={uniqueHospitals.toLocaleString()} variant="navy" />
    </div>
  )
}
