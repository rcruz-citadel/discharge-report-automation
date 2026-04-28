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
    <div className="min-w-0">
      <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-0.5">{label}</p>
      <p className="text-[14.4px] font-semibold text-text-primary truncate" title={orDash(value as string)}>{orDash(value as string)}</p>
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
    /*
     * Outer shell: holds shape, border, shadow, and border-radius.
     * Does NOT scroll — this keeps the header permanently visible.
     * max-height + overflow live on the inner scroll container below.
     */
    <div
      ref={panelRef}
      className="panel-enter flex flex-col bg-surface rounded-xl overflow-hidden"
      style={{
        border: '1.5px solid #132e45',
        boxShadow: '0 6px 24px rgba(19,46,69,0.14)',
        maxHeight: 'calc(100vh - 48px)',
      }}
      role="complementary"
      aria-label="Patient detail"
      onKeyDown={handleKeyDown}
    >
      {/* ── Sticky header — always visible, never scrolls away ── */}
      <div
        className="shrink-0 px-5 py-4 flex items-center justify-between"
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

      {/* Scrollable body — fills remaining height in the fixed-height column wrapper */}
      <div className="flex-1 flex flex-col overflow-y-auto min-h-0">
        {/* Section 1 — Patient demographics, provider & contact */}
        <div className="px-5 py-4 border-b border-border-light">
          <p className="text-[10.5px] font-bold uppercase tracking-wider mb-2" style={{ color: '#556e81' }}>
            Patient &amp; Provider
          </p>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <Field label="Member ID" value={row.insurance_member_id} />
            <Field label="Date of Birth" value={row.birth_date} />
            <Field label="Phone" value={row.phone} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Practice" value={row.practice} />
            <Field label="Provider" value={row.provider_name} />
            <Field label="Payer" value={row.payer_name} />
          </div>
        </div>

        {/* Section 2 — Hospital & diagnosis */}
        <div className="px-5 py-4 border-b border-border-light">
          <p className="text-[10.5px] font-bold uppercase tracking-wider mb-2" style={{ color: '#556e81' }}>
            Hospitalization &amp; Diagnosis
          </p>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <Field label="Hospital" value={row.discharge_hospital} />
            <Field label="Admit Date" value={row.admit_date ? formatDate(row.admit_date) : null} />
            <Field label="Discharge Date" value={formatDate(row.discharge_date)} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Stay Type" value={row.stay_type} />
            <Field label="LOS" value={row.length_of_stay != null ? `${row.length_of_stay} day${row.length_of_stay !== 1 ? 's' : ''}` : null} />
            <Field label="Disposition" value={row.disposition} />
          </div>
          {(row.dx_code || row.description) && (
            <div className="mt-3">
              <Field label="Diagnosis" value={row.dx_code ? `${row.dx_code} — ${row.description}` : row.description} />
            </div>
          )}
        </div>

        {/* Outreach status form — pb-6 ensures content never kisses the card edge */}
        <div className="px-5 py-4 pb-6">
          <OutreachStatusForm row={row} onSuccess={onSaveSuccess} onCancel={onClose} />
        </div>
      </div>
    </div>
  )
}
