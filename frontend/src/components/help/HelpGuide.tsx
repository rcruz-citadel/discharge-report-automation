import { StatusPill } from '../ui/StatusPill'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2
        className="text-[11px] font-bold tracking-widest uppercase mb-4"
        style={{ color: '#556e81' }}
      >
        {title}
      </h2>
      {children}
    </section>
  )
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl p-5 mb-3"
      style={{ background: '#ffffff', border: '1.5px solid #dde4eb' }}
    >
      {children}
    </div>
  )
}

function TabCard({
  label,
  timeframe,
  description,
  color,
}: {
  label: string
  timeframe: string
  description: string
  color: string
}) {
  return (
    <Card>
      <div className="flex items-center gap-3 mb-2">
        <span
          className="text-[12px] font-bold px-3 py-1 rounded-full text-white"
          style={{ backgroundColor: color }}
        >
          {label}
        </span>
        <span className="text-[11px] font-semibold" style={{ color: '#556e81' }}>
          {timeframe}
        </span>
      </div>
      <p className="text-[13px] leading-relaxed m-0" style={{ color: '#3d5468' }}>
        {description}
      </p>
    </Card>
  )
}

function StatusRow({
  status,
  who,
  description,
}: {
  status: Parameters<typeof StatusPill>[0]['status']
  who: string
  description: string
}) {
  return (
    <div className="flex items-start gap-4 py-3" style={{ borderBottom: '1px solid #edf2f7' }}>
      <div className="shrink-0 w-40">
        <StatusPill status={status} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-semibold mb-0.5" style={{ color: '#132e45' }}>
          {who}
        </p>
        <p className="text-[12px] leading-relaxed m-0" style={{ color: '#556e81' }}>
          {description}
        </p>
      </div>
    </div>
  )
}

function ContextBadgeRow({
  dotColor,
  label,
  textColor,
  description,
}: {
  dotColor: string
  label: string
  textColor: string
  description: string
}) {
  return (
    <div className="flex items-start gap-4 py-3" style={{ borderBottom: '1px solid #edf2f7' }}>
      <div className="shrink-0 w-40 flex items-center gap-1.5 pt-0.5">
        <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: dotColor, flexShrink: 0, display: 'inline-block' }} />
        <span className="text-[11px] font-semibold" style={{ color: textColor }}>{label}</span>
      </div>
      <p className="text-[12px] leading-relaxed m-0" style={{ color: '#556e81' }}>
        {description}
      </p>
    </div>
  )
}

function DeadlineBadge({
  label,
  bg,
  color,
  description,
}: {
  label: string
  bg: string
  color: string
  description: string
}) {
  return (
    <div className="flex items-center gap-4 py-3" style={{ borderBottom: '1px solid #edf2f7' }}>
      <span
        className="shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold w-24 justify-center"
        style={{ backgroundColor: bg, color }}
      >
        {label}
      </span>
      <p className="text-[12px] leading-relaxed m-0" style={{ color: '#556e81' }}>
        {description}
      </p>
    </div>
  )
}

export function HelpGuide() {
  return (
    <div
      className="max-w-3xl mx-auto py-6 px-2"
    >
      {/* Page title */}
      <div className="mb-8">
        <h1 className="text-[22px] font-bold mb-1" style={{ color: '#132e45' }}>
          Coordinator Guide
        </h1>
        <p className="text-[13px] m-0" style={{ color: '#718096' }}>
          How to use the TCM Outreach Tracker — tabs, statuses, deadlines, and workflow.
        </p>
      </div>

      {/* ── Queues ── */}
      <Section title="The Three Queues">
        <TabCard
          label="Immediate"
          timeframe="Discharged within 48 hours"
          description="Patients who were discharged in the last two days. CMS requires first contact within 48 hours of discharge to qualify for TCM billing — these records need outreach now. Sort order: fewest days remaining first."
          color="#c53030"
        />
        <TabCard
          label="Active"
          timeframe="Past 48-hour window, TCM window still open"
          description="The 48-hour call window has passed, but the 30-day TCM window (7 days for ER) is still open. Outreach is still possible and should be attempted. Records showing '48h Missed' missed the initial call but can still be recovered here."
          color="#1b4459"
        />
        <TabCard
          label="Past Deadline"
          timeframe="TCM window expired"
          description="The full TCM window has closed. No billing opportunity remains. The only action needed is dropping the discharge summary in the EMR when possible. Records here are for documentation purposes only."
          color="#718096"
        />
      </Section>

      {/* ── Statuses ── */}
      <Section title="Outreach Statuses">
        <Card>
          <p className="text-[12px] font-semibold mb-3" style={{ color: '#132e45' }}>
            Set by coordinators
          </p>
          <StatusRow
            status="no_outreach"
            who="Coordinator"
            description="Default state. No outreach has been attempted yet. Records in this state on Immediate need action today."
          />
          <StatusRow
            status="outreach_made"
            who="Coordinator"
            description="At least one contact attempt has been made (phone call, voicemail, portal message, etc.). Continue following up until contact is established."
          />
          <StatusRow
            status="outreach_complete"
            who="Coordinator"
            description="Contact was established and TCM services are complete. No further outreach needed — this record is resolved."
          />
          <StatusRow
            status="no_outreach_required"
            who="Coordinator"
            description="An exception applies — patient is in hospice, declined services, or is otherwise not a TCM candidate. No outreach will be performed."
          />

          <p className="text-[12px] font-semibold mb-3 mt-5" style={{ color: '#132e45' }}>
            Set automatically by the system
          </p>
          <StatusRow
            status="failed"
            who="System"
            description="The TCM window has expired with no outreach completed. Set automatically by the system. Records may also show a context badge (48h Missed or Late ADT) — see the Context Badges section below for details."
          />
          <StatusRow
            status="late_delivery"
            who="System"
            description="The ADT notification arrived more than 2 days after discharge. The team could not have acted on the 48-hour window. Outreach is still possible within the remaining TCM window."
          />
        </Card>
      </Section>

      {/* ── Context badges ── */}
      <Section title="Context Badges">
        <Card>
          <p className="text-[12px] leading-relaxed mb-3" style={{ color: '#3d5468' }}>
            Some records show a small badge next to their outreach status. These are informational — they explain <em>why</em> a record is flagged, not what to do differently. The action is always the same: make contact and mark it accordingly.
          </p>
          <ContextBadgeRow
            dotColor="#d69e2e"
            label="48h Missed"
            textColor="#975a16"
            description="The 48-hour first-contact window passed without outreach being initiated. The record was in the system in time — the window was missed. Outreach can still be made if the 30-day TCM window is open. These records appear in the Active tab."
          />
          <ContextBadgeRow
            dotColor="#93c5fd"
            label="Late ADT"
            textColor="#3b82f6"
            description="The insurance company sent the discharge notification late — more than 2 days after the patient was discharged. The team could not have acted on the 48-hour window because the record didn't exist yet. This is a payer data issue, not a coordinator miss. Outreach is still possible within the remaining TCM window."
          />
          <p className="text-[11px] mt-3 mb-0 leading-relaxed" style={{ color: '#a0aec0' }}>
            These badges disappear once a record is resolved (marked Outreach Complete or No Outreach Required). The underlying data is always preserved for reporting.
          </p>
        </Card>
      </Section>

      {/* ── Deadline badges ── */}
      <Section title="Deadline Badges">
        <Card>
          <div style={{ borderBottom: '1px solid #edf2f7' }} className="pb-2 mb-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide m-0" style={{ color: '#718096' }}>
              Badge → Meaning
            </p>
          </div>
          <DeadlineBadge
            label="5d left"
            bg="#e6ffed"
            color="#22753a"
            description="More than 3 days remaining in the TCM window. No immediate urgency."
          />
          <DeadlineBadge
            label="2d left"
            bg="#fefcbf"
            color="#975a16"
            description="3 days or fewer remaining. Escalate — contact must be made very soon."
          />
          <DeadlineBadge
            label="1d left"
            bg="#feebc8"
            color="#c05621"
            description="Only 1 day remaining. Last chance — outreach must happen today."
          />
          <DeadlineBadge
            label="Overdue"
            bg="#feebc8"
            color="#c05621"
            description="Past the TCM deadline. The system will auto-fail this record overnight. Drop the discharge summary in the EMR."
          />
          <DeadlineBadge
            label="—"
            bg="#edf2f7"
            color="#718096"
            description="Record is on the Past Deadline tab. No countdown is shown."
          />
        </Card>
      </Section>

      {/* ── TCM windows ── */}
      <Section title="TCM Time Windows">
        <Card>
          <div className="grid grid-cols-2 gap-4">
            <div
              className="rounded-lg p-4"
              style={{ background: '#ebf8ff', border: '1px solid #90cdf4' }}
            >
              <p className="text-[12px] font-bold mb-1" style={{ color: '#2b6cb0' }}>
                Standard (Inpatient / SNF / Other)
              </p>
              <p className="text-[22px] font-bold m-0" style={{ color: '#132e45' }}>30 days</p>
              <p className="text-[11px] mt-1 m-0" style={{ color: '#4a7fa5' }}>
                First contact required within 48 hours of discharge.
              </p>
            </div>
            <div
              className="rounded-lg p-4"
              style={{ background: '#fff5f5', border: '1px solid #feb2b2' }}
            >
              <p className="text-[12px] font-bold mb-1" style={{ color: '#c53030' }}>
                Emergency (ER stays)
              </p>
              <p className="text-[22px] font-bold m-0" style={{ color: '#132e45' }}>7 days</p>
              <p className="text-[11px] mt-1 m-0" style={{ color: '#9b2c2c' }}>
                Shorter window — ER discharges need faster action.
              </p>
            </div>
          </div>
          <p
            className="text-[12px] mt-4 mb-0 leading-relaxed"
            style={{ color: '#556e81' }}
          >
            Both windows start on the discharge date. Once a window closes, the record moves to
            Past Deadline and TCM billing is no longer available. Home health and hospice
            discharges are excluded from outreach tracking.
          </p>
        </Card>
      </Section>

      {/* ── Workflow ── */}
      <Section title="Typical Workflow">
        <Card>
          <ol className="m-0 p-0 list-none flex flex-col gap-3">
            {[
              ['Start on Immediate', 'Work through all records discharged in the last 48 hours. These are your highest priority. Log an attempt or set status to Outreach Made.'],
              ['Move to Active', 'Records you couldn\'t reach on day 1–2 stay here. Continue follow-up until contact is made or the window closes.'],
              ['Use the detail panel', 'Click any row to open the detail panel on the right. Set the status, add notes, log an attempt, and save.'],
              ['Log attempts', 'Each time you try to reach a patient, log an attempt in the detail panel. After 3 attempts the system can auto-complete the record.'],
              ['Drop summary in EMR', 'For Past Deadline records, drop the discharge summary in the EMR and check the box in the detail panel.'],
              ['Use No Outreach Needed for exceptions', 'If a patient is in hospice, declined services, or is otherwise not a TCM candidate, set this status to remove them from the active queue.'],
            ].map(([step, detail], i) => (
              <li key={i} className="flex gap-3">
                <span
                  className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold text-white mt-0.5"
                  style={{ backgroundColor: '#132e45' }}
                >
                  {i + 1}
                </span>
                <div>
                  <p className="text-[13px] font-semibold mb-0.5 mt-0" style={{ color: '#132e45' }}>{step}</p>
                  <p className="text-[12px] leading-relaxed m-0" style={{ color: '#556e81' }}>{detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </Card>
      </Section>

      {/* ── Filters ── */}
      <Section title="Filters & Export">
        <Card>
          <p className="text-[13px] leading-relaxed m-0" style={{ color: '#3d5468' }}>
            Use the left sidebar to filter by <strong>practice</strong>, <strong>payer</strong>,{' '}
            <strong>line of business</strong>, <strong>stay type</strong>, <strong>discharge date range</strong>,
            and <strong>assignee</strong>. You can also filter by outreach status using the legend
            above the table — click any status chip to show only those records.
          </p>
          <p className="text-[13px] leading-relaxed mt-3 mb-0" style={{ color: '#3d5468' }}>
            The <strong>Export CSV</strong> button (top-right of each tab) exports the current
            filtered view. Use this for reporting or payer portal uploads.
          </p>
        </Card>
      </Section>

      <p className="text-[11px] text-center mt-2" style={{ color: '#a0aec0' }}>
        Questions? Contact your manager or reach out to the care analytics team.
      </p>
    </div>
  )
}
