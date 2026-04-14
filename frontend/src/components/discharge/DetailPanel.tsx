import { useEffect, useRef, type KeyboardEvent } from 'react'
import type { DischargeRecord } from '../../types/discharge'
import { OutreachStatusForm } from './OutreachStatusForm'
import { formatDate, orDash } from '../../lib/utils'

interface DetailPanelProps {
  row: DischargeRecord
  onClose: () => void
  onSaveSuccess: (patientName: string) => void
}

interface FieldProps {
  label: string
  value: string | number | null | undefined
}

function Field({ label, value }: FieldProps) {
  return (
    <div>
      <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-0.5">{label}</p>
      <p className="text-[14.4px] font-semibold text-text-primary">{orDash(value as string)}</p>
    </div>
  )
}

/**
 * Detail panel that slides in from the right when a table row is selected.
 * Shows patient info grid and the OutreachStatusForm.
 * Spec: 4.5 Table + Detail Panel Split Layout, 5.5 Detail Panel
 */
export function DetailPanel({ row, onClose, onSaveSuccess }: DetailPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  // Focus trap: move focus to first interactive element when panel opens
  useEffect(() => {
    const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    focusable?.[0]?.focus()
  }, [row.event_id])

  // Close on Escape
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      onClose()
    }
  }

  return (
    <div
      ref={panelRef}
      className="panel-enter flex flex-col bg-surface rounded-xl overflow-hidden"
      style={{
        border: '1.5px solid #132e45',
        boxShadow: '0 4px 18px rgba(19,46,69,0.10)',
        height: 'fit-content',
        maxHeight: 'calc(100vh - 160px)',
        overflowY: 'auto',
      }}
      role="complementary"
      aria-label="Patient detail"
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <div
        className="px-5 py-4 flex items-center justify-between"
        style={{ background: 'linear-gradient(135deg, #132e45 0%, #1b4459 100%)' }}
      >
        <div>
          <h2 className="text-[16px] font-bold text-white">
            {row.patient_name ?? 'Unknown Patient'}
          </h2>
          <p className="text-[12px] text-[#a8c4d8] mt-0.5">
            Discharged {formatDate(row.discharge_date)}
          </p>
        </div>
        <button
          onClick={onClose}
          aria-label="Close detail panel"
          className="w-7 h-7 flex items-center justify-center rounded-md text-[#a8c4d8] hover:text-white hover:bg-white/10 transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Patient info grid */}
      <div className="px-5 py-4 border-b border-border-light">
        <div className="grid grid-cols-3 gap-3 mb-3">
          <Field label="Practice" value={row.practice} />
          <Field label="Payer" value={row.payer_name} />
          <Field label="Hospital" value={row.discharge_hospital} />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Diagnosis" value={row.dx_code ? `${row.dx_code} — ${row.description}` : row.description} />
          <Field label="LOS" value={row.length_of_stay != null ? `${row.length_of_stay} day${row.length_of_stay !== 1 ? 's' : ''}` : null} />
          <Field label="Disposition" value={row.disposition} />
        </div>
        {row.insurance_member_id && (
          <div className="mt-3">
            <Field label="Member ID" value={row.insurance_member_id} />
          </div>
        )}
      </div>

      {/* Outreach status form */}
      <div className="px-5 py-4">
        <OutreachStatusForm row={row} onSuccess={onSaveSuccess} onCancel={onClose} />
      </div>
    </div>
  )
}
