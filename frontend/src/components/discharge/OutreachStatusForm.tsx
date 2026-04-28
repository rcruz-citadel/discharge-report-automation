import { useState, type FormEvent } from 'react'
import type { DischargeRecord, OutreachStatus } from '../../types/discharge'
import { OUTREACH_STATUS_COLORS, OUTREACH_STATUS_LABELS, getDaysRemaining, getQueueBucket } from '../../types/discharge'
import { useUpsertOutreach, useAttempts, useLogAttempt } from '../../hooks/useOutreach'
import { Button } from '../ui/Button'
import { formatDateTime } from '../../lib/utils'

// ── Workflow guidance content ─────────────────────────────────────────────────

const WORKFLOW_STEPS = [
  {
    step: '1',
    title: 'Check the chart first',
    detail: 'Before calling, verify in the EMR that an appointment has not already been scheduled.',
  },
  {
    step: '2',
    title: 'Outreach within 48 hours',
    detail: 'TCM requires contact within 2 business days of discharge. Use the EMR for the most accurate phone number.',
  },
  {
    step: '3',
    title: 'Log each attempt',
    detail: 'Tap "+ Log Attempt" after every call — voicemail counts. After 3 attempts the record auto-completes.',
  },
  {
    step: '4',
    title: 'SNF/Rehab transfers',
    detail: 'If the patient went to a SNF after hospital discharge, reach out on hospital discharge, note the transfer, and wait for the SNF discharge notification to restart the clock.',
  },
  {
    step: '5',
    title: 'Drop the discharge summary',
    detail: 'For records past the outreach window (Low Priority), drop the discharge summary in the EMR chart and check the box below. No time limit for this step.',
  },
]

const STATUS_TIPS: Partial<Record<OutreachStatus, string>> = {
  late_delivery: 'ADT arrived after the 48-hour window. You may still have time to reach the patient within the 7/30-day TCM window.',
  no_outreach_required: 'No TCM action needed for this record (e.g. deceased, transferred to coordinated care). Use this only when appropriate.',
  outreach_complete: 'Mark complete when the patient has been engaged, an appointment is scheduled, OR all 3 outreach attempts are exhausted.',
}

// ── Attempt section ───────────────────────────────────────────────────────────

interface AttemptSectionProps {
  eventId: string
  dischargeDate: string
  onAutoComplete?: () => void
}

function AttemptSection({ eventId, dischargeDate, onAutoComplete }: AttemptSectionProps) {
  const { data: attempts = [], isLoading } = useAttempts(eventId, dischargeDate)
  const mutation = useLogAttempt(eventId, dischargeDate)
  const atMax = attempts.length >= 3

  const handleLog = () => {
    mutation.mutate(undefined, {
      onSuccess: (data) => {
        if (data.auto_completed && onAutoComplete) {
          onAutoComplete()
        }
      },
    })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider">
          Outreach Attempts
        </p>
        <span
          className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
          style={{
            backgroundColor: atMax ? '#fed7d7' : '#edf2f7',
            color: atMax ? '#c53030' : '#718096',
          }}
        >
          {attempts.length} / 3
        </span>
      </div>

      {isLoading ? (
        <p className="text-[12px] text-text-muted">Loading...</p>
      ) : attempts.length === 0 ? (
        <p className="text-[12px] text-text-muted italic">No attempts logged yet.</p>
      ) : (
        <ol className="flex flex-col gap-1.5 mb-3">
          {attempts.map(a => (
            <li key={a.id} className="flex items-start gap-2 text-[12px]">
              <span
                className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white mt-0.5"
                style={{ backgroundColor: '#132e45' }}
              >
                {a.attempt_number}
              </span>
              <span className="text-text-primary">
                <span className="font-semibold">{a.attempted_by}</span>
                {' · '}
                <span className="text-text-muted">{formatDateTime(a.attempted_at)}</span>
              </span>
            </li>
          ))}
        </ol>
      )}

      {atMax ? (
        <p className="text-[12px] text-text-muted italic">Max attempts reached — record auto-completed.</p>
      ) : (
        <button
          type="button"
          onClick={handleLog}
          disabled={mutation.isPending}
          className="text-[12px] font-semibold px-3 py-1.5 rounded-md transition-colors disabled:opacity-60"
          style={{
            backgroundColor: '#edf2f7',
            color: '#132e45',
            border: '1.5px solid #d0dae3',
          }}
        >
          {mutation.isPending ? 'Logging...' : '+ Log Attempt'}
        </button>
      )}

      {mutation.isError && (
        <p className="text-[12px] mt-1" style={{ color: '#c53030' }}>
          Failed to log attempt. Try again.
        </p>
      )}
    </div>
  )
}

// ── Days-remaining banner ─────────────────────────────────────────────────────

function DaysRemainingBanner({ row }: { row: DischargeRecord }) {
  const bucket = getQueueBucket(row)
  if (bucket === 'low_priority') return null

  const daysLeft = getDaysRemaining(row)
  const isER = row.stay_type?.toLowerCase().includes('emergency')
  const windowLabel = isER ? '7-day ER' : '30-day'

  let bg: string
  let color: string
  let label: string

  if (daysLeft <= 0) {
    bg = '#fed7d7'; color = '#c53030'; label = 'Window closed'
  } else if (daysLeft === 1) {
    bg = '#fed7d7'; color = '#c53030'; label = '1 day left'
  } else if (daysLeft <= 3) {
    bg = '#fefcbf'; color = '#975a16'; label = `${daysLeft} days left`
  } else {
    bg = '#e6ffed'; color = '#22753a'; label = `${daysLeft} days left`
  }

  return (
    <div
      className="flex items-center justify-between px-3 py-2 rounded-md text-[12px] font-semibold"
      style={{ backgroundColor: bg, color }}
    >
      <span>{windowLabel} TCM window</span>
      <span>{label}</span>
    </div>
  )
}

// ── Workflow help accordion ───────────────────────────────────────────────────

function WorkflowHelp() {
  const [open, setOpen] = useState(false)
  return (
    <div
      className="rounded-md overflow-hidden"
      style={{ border: '1px solid #d0dae3' }}
    >
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-[12px] font-semibold text-text-secondary hover:bg-[#f7f9fb] transition-colors"
      >
        <span>Workflow Guide</span>
        <span style={{ fontSize: '10px' }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 flex flex-col gap-2" style={{ backgroundColor: '#f7f9fb' }}>
          {WORKFLOW_STEPS.map(s => (
            <div key={s.step} className="flex gap-2">
              <span
                className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white mt-0.5"
                style={{ backgroundColor: '#132e45' }}
              >
                {s.step}
              </span>
              <div>
                <p className="text-[12px] font-semibold text-text-primary">{s.title}</p>
                <p className="text-[11px] text-text-muted">{s.detail}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main form ─────────────────────────────────────────────────────────────────

interface OutreachStatusFormProps {
  row: DischargeRecord
  onSuccess: (patientName: string) => void
  onCancel: () => void
}

export function OutreachStatusForm({ row, onSuccess, onCancel }: OutreachStatusFormProps) {
  const [status, setStatus] = useState<OutreachStatus>(row.outreach_status)
  const [notes, setNotes] = useState(row.outreach_notes)
  const [summaryDropped, setSummaryDropped] = useState(row.discharge_summary_dropped)
  const mutation = useUpsertOutreach()

  const bucket = getQueueBucket(row)
  const isLowPriority = bucket === 'low_priority'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await mutation.mutateAsync({
      event_id: row.event_id,
      discharge_date: row.discharge_date,
      status,
      notes,
      discharge_summary_dropped: summaryDropped,
    })
    onSuccess(row.patient_name ?? 'Patient')
  }

  const statuses: OutreachStatus[] = [
    'no_outreach',
    'outreach_made',
    'outreach_complete',
    'failed',
    'late_delivery',
    'no_outreach_required',
  ]

  const tip = STATUS_TIPS[status]

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Days remaining banner */}
      <DaysRemainingBanner row={row} />

      {/* Status segmented button group */}
      <div>
        <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-2">
          Outreach Status
        </p>
        <div className="grid grid-cols-3 gap-2" role="group" aria-label="Outreach status">
          {statuses.map(s => {
            const isSelected = status === s
            const colors = OUTREACH_STATUS_COLORS[s]
            return (
              <button
                key={s}
                type="button"
                role="radio"
                aria-checked={isSelected}
                disabled={mutation.isPending}
                onClick={() => setStatus(s)}
                className="flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-[11px] font-semibold transition-all duration-150 disabled:opacity-60"
                style={{
                  backgroundColor: isSelected ? colors.btnBg : '#f7f9fb',
                  border: `1.5px solid ${isSelected ? colors.btnBorder : '#d0dae3'}`,
                  color: isSelected ? colors.btnText : '#2a3f50',
                }}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: isSelected ? colors.dot : '#cbd5e0' }}
                  aria-hidden="true"
                />
                {OUTREACH_STATUS_LABELS[s]}
              </button>
            )
          })}
        </div>
        {tip && (
          <p className="text-[11px] text-text-muted mt-2 italic">{tip}</p>
        )}
      </div>

      {/* Notes textarea */}
      <div>
        <label
          htmlFor="outreach-notes"
          className="block text-[11px] font-bold text-text-muted uppercase tracking-wider mb-1"
        >
          Notes
        </label>
        <textarea
          id="outreach-notes"
          value={notes}
          onChange={e => setNotes(e.target.value)}
          disabled={mutation.isPending}
          rows={3}
          placeholder="Add outreach notes..."
          className="w-full rounded-md text-[13px] text-text-primary p-2 resize-none disabled:opacity-60 transition-shadow duration-150"
          style={{
            backgroundColor: '#f7f9fb',
            border: '1.5px solid #d0dae3',
            height: '80px',
            outline: 'none',
          }}
          onFocus={e => {
            e.currentTarget.style.borderColor = '#132e45'
            e.currentTarget.style.boxShadow = '0 0 0 2px rgba(19,46,69,0.15)'
          }}
          onBlur={e => {
            e.currentTarget.style.borderColor = '#d0dae3'
            e.currentTarget.style.boxShadow = 'none'
          }}
        />
      </div>

      {/* Discharge summary dropped checkbox — only shown for low priority records */}
      {isLowPriority && (
        <label className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={summaryDropped}
            onChange={e => setSummaryDropped(e.target.checked)}
            disabled={mutation.isPending}
            className="w-4 h-4 rounded accent-navy disabled:opacity-60 cursor-pointer"
          />
          <span className="text-[13px] font-semibold text-text-primary group-hover:text-navy transition-colors">
            Discharge Summary Dropped in EMR
          </span>
        </label>
      )}

      {/* Attempt tracking */}
      <AttemptSection
        eventId={row.event_id}
        dischargeDate={row.discharge_date}
        onAutoComplete={() => setStatus('outreach_complete')}
      />

      {/* Workflow help */}
      <WorkflowHelp />

      {/* Last updated */}
      {row.outreach_updated_by && (
        <p className="text-[12px] text-text-muted">
          Last updated by{' '}
          <span className="font-bold">{row.outreach_updated_by}</span>
          {row.outreach_updated_at ? ` on ${formatDateTime(row.outreach_updated_at)}` : ''}
        </p>
      )}

      {/* Mutation error */}
      {mutation.isError && (
        <div
          role="alert"
          aria-live="assertive"
          className="px-3 py-2 rounded-md text-[12px] font-medium"
          style={{ backgroundColor: '#fee2e2', color: '#991b1b' }}
        >
          Failed to save. Please try again.
        </div>
      )}

      {/* Save / Cancel */}
      <div className="flex gap-2">
        <Button
          type="submit"
          variant="primary"
          isLoading={mutation.isPending}
          disabled={mutation.isPending}
          className="flex-1 py-2 text-[14px]"
        >
          Save
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          disabled={mutation.isPending}
          className="px-4 py-2 text-[13px]"
        >
          Cancel
        </Button>
      </div>
    </form>
  )
}
