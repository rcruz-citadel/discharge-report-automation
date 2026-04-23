import { useState, type FormEvent } from 'react'
import type { DischargeRecord, OutreachStatus } from '../../types/discharge'
import { OUTREACH_STATUS_COLORS, OUTREACH_STATUS_LABELS } from '../../types/discharge'
import { useUpsertOutreach, useAttempts, useLogAttempt } from '../../hooks/useOutreach'
import { Button } from '../ui/Button'
import { formatDateTime } from '../../lib/utils'

interface AttemptSectionProps {
  eventId: string
  dischargeDate: string
}

function AttemptSection({ eventId, dischargeDate }: AttemptSectionProps) {
  const { data: attempts = [], isLoading } = useAttempts(eventId, dischargeDate)
  const mutation = useLogAttempt(eventId, dischargeDate)
  const atMax = attempts.length >= 3

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
        <p className="text-[12px] text-text-muted italic">Max attempts reached.</p>
      ) : (
        <button
          type="button"
          onClick={() => mutation.mutate()}
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

interface OutreachStatusFormProps {
  row: DischargeRecord
  onSuccess: (patientName: string) => void
  onCancel: () => void
}

/**
 * Segmented status button group + notes textarea + Save/Cancel.
 * Spec: 4.12 Status Selection -> Save, 5.5 Detail Panel
 */
export function OutreachStatusForm({ row, onSuccess, onCancel }: OutreachStatusFormProps) {
  const [status, setStatus] = useState<OutreachStatus>(row.outreach_status)
  const [notes, setNotes] = useState(row.outreach_notes)
  const mutation = useUpsertOutreach()

  const isDirty = status !== row.outreach_status || notes !== row.outreach_notes

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await mutation.mutateAsync({
      event_id: row.event_id,
      discharge_date: row.discharge_date,
      status,
      notes,
    })
    onSuccess(row.patient_name ?? 'Patient')
  }

  const statuses: OutreachStatus[] = ['no_outreach', 'outreach_made', 'outreach_complete', 'failed']

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Status segmented button group */}
      <div>
        <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-2">
          Outreach Status
        </p>
        <div
          className="flex gap-2"
          role="group"
          aria-label="Outreach status"
        >
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
                className="flex-1 flex items-center justify-center gap-2 py-2 px-2 rounded-md text-[12px] font-semibold transition-all duration-150 disabled:opacity-60"
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

      {/* Attempt tracking */}
      <AttemptSection eventId={row.event_id} dischargeDate={row.discharge_date} />

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
          disabled={!isDirty}
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
