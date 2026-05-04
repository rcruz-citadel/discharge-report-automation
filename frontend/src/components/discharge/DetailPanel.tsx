import { useEffect, useRef, type KeyboardEvent } from 'react'
import type { DischargeRecord } from '../../types/discharge'
import { OutreachStatusForm } from './OutreachStatusForm'
import { formatDate, orDash } from '../../lib/utils'

interface DetailPanelProps {
  row: DischargeRecord
  onClose: () => void
  onSaveSuccess: (patientName: string, newStatus?: import('../../types/discharge').OutreachStatus) => void
  /** When true, shows an info banner indicating the record is in the Resolved tab. */
  isResolved?: boolean
}

interface FieldProps {
  label: string
  value: string | number | null | undefined
  wrap?: boolean
  warn?: boolean
  warnTitle?: string
}

function Field({ label, value, wrap, warn, warnTitle }: FieldProps) {
  const display = orDash(value as string)
  const isEmpty = display === '—'
  const showWarning = warn && isEmpty

  return (
    <div className="min-w-0">
      <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-0.5">{label}</p>
      {showWarning ? (
        <span
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold"
          style={{ backgroundColor: '#fefcbf', color: '#975a16' }}
          title={warnTitle}
        >
          ⚠ Unknown
        </span>
      ) : (
        <p
          className={`text-[14.4px] font-semibold text-text-primary ${wrap ? 'break-words leading-snug' : 'truncate'}`}
          title={wrap ? undefined : display}
        >
          {display}
        </p>
      )}
    </div>
  )
}

/**
 * Detail panel that slides in from the right when a table row is selected.
 * Shows patient info grid and the OutreachStatusForm.
 * Spec: 4.5 Table + Detail Panel Split Layout, 5.5 Detail Panel
 */
export function DetailPanel({ row, onClose, onSaveSuccess, isResolved }: DetailPanelProps) {
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
      className="panel-enter flex flex-col bg-surface rounded-xl overflow-hidden h-full"
      style={{
        border: '1.5px solid #132e45',
        boxShadow: '0 6px 24px rgba(19,46,69,0.14)',
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
          style={{ border: '1px solid rgba(255,255,255,0.15)' }}
        >
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
            <line x1="1" y1="1" x2="10" y2="10"/>
            <line x1="10" y1="1" x2="1" y2="10"/>
          </svg>
        </button>
      </div>

      {/* Scrollable body — fills remaining height in the fixed-height column wrapper */}
      <div className="flex-1 flex flex-col overflow-y-auto min-h-0">
        {/* Resolved banner — shown when the record is viewed from the Resolved tab */}
        {isResolved && (
          <div
            className="shrink-0 flex items-center gap-2 px-4 py-2 text-[12px] font-semibold"
            style={{ backgroundColor: '#f0fdf4', borderBottom: '1px solid #bbf7d0', color: '#166534' }}
            role="status"
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="shrink-0">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>
              This record is resolved — update the status below to return it to your work queue.
            </span>
          </div>
        )}

        {/* Original failure indicator — shown when a coordinator has overridden a previously auto-flagged record */}
        {row.original_failure_reason && row.outreach_status !== 'failed' && (
          <div
            className="shrink-0 px-4 py-2 text-[11.5px]"
            style={{ backgroundColor: '#f8f9fa', borderBottom: '1px solid #e9ecef', color: '#6c757d' }}
          >
            Originally auto-flagged:{' '}
            <span className="font-medium">
              {row.original_failure_reason === 'missed_48h'
                ? 'missed 48h window'
                : row.original_failure_reason === 'missed_tcm_window'
                ? 'missed TCM window'
                : 'late delivery'}
            </span>
          </div>
        )}

        {/* Section 1 — Patient demographics, provider & contact */}
        <div className="px-5 py-4 border-b border-border-light">
          <p className="text-[11.5px] font-bold uppercase tracking-wider mb-2" style={{ color: '#556e81' }}>
            Patient &amp; Provider
          </p>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <Field label="Member ID" value={row.insurance_member_id} />
            <Field label="Date of Birth" value={row.birth_date} />
            <Field label="Phone" value={row.phone && row.phone !== '0' ? row.phone : null} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Practice" value={row.practice} />
            <Field label="Provider" value={row.provider_name} />
            <Field label="Payer" value={row.payer_name} />
          </div>
        </div>

        {/* Section 2 — Hospital & diagnosis */}
        <div className="px-5 py-4 border-b border-border-light">
          <p className="text-[11.5px] font-bold uppercase tracking-wider mb-2" style={{ color: '#556e81' }}>
            Hospitalization &amp; Diagnosis
          </p>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <Field label="Hospital" value={row.discharge_hospital} warn warnTitle="Hospital unknown — check payer portal" />
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
              <Field label="Diagnosis" value={row.dx_code ? `${row.dx_code} — ${row.description}` : row.description} wrap />
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
