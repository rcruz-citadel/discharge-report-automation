import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { DischargeRecord, OutreachStatus } from '../types/discharge'
import { getDaysRemaining, getQueueBucket } from '../types/discharge'
import { useDischarges } from '../hooks/useDischarges'
import { useFilters } from '../hooks/useFilters'
import { useAuth } from '../auth/useAuth'
import { AppShell } from '../components/layout/AppShell'
import { AppHeader } from '../components/layout/AppHeader'
import { Sidebar } from '../components/layout/Sidebar'
import { FilterSidebar } from '../components/filters/FilterSidebar'
import { DischargeTable } from '../components/discharge/DischargeTable'
import { DetailPanel } from '../components/discharge/DetailPanel'
import { StatChipRow } from '../components/ui/StatChipRow'
import { OutreachLegend } from '../components/discharge/OutreachLegend'
import { ManagerDashboard } from '../components/manager/ManagerDashboard'
import { useToast } from '../components/ui/Toast'
import { fetchMetaFilters } from '../api/meta'
import { exportToCsv, fileTimestamp } from '../lib/utils'

type TabId = 'immediate' | 'active' | 'low_priority' | 'manager'

const CSV_COLUMNS = [
  'patient_name', 'birth_date', 'insurance_member_id', 'phone',
  'discharge_date', 'admit_date', 'practice', 'payer_name',
  'lob_name', 'stay_type', 'discharge_hospital', 'length_of_stay',
  'disposition', 'dx_code', 'description',
  'patient_address', 'city', 'zip_code', 'state',
  'outreach_status', 'outreach_notes', 'outreach_updated_by', 'discharge_summary_dropped',
]

const TAB_DESCRIPTIONS: Record<TabId, string> = {
  immediate: 'Discharged within the last 48 hours — outreach needed now',
  active: 'Past 48-hour window but still within the 7/30-day TCM deadline',
  low_priority: 'Past TCM deadline — drop the discharge summary in the EMR when possible',
  manager: 'Manager Dashboard',
}

const TAB_LABELS: Record<TabId, string> = {
  immediate: 'Immediate',
  active: 'Active',
  low_priority: 'Past Deadline',
  manager: 'Manager',
}

export function DashboardPage() {
  const { user, isManager } = useAuth()
  const { filters, setFilter, setAssignee, clearAll, hasActiveFilters } = useFilters()
  const [activeTab, setActiveTab] = useState<TabId>('immediate')
  const [selectedRow, setSelectedRow] = useState<DischargeRecord | null>(null)
  const { show: showToast, ToastContainer } = useToast()

  const { data: dischargData, isLoading: dischargesLoading } = useDischarges()
  const { data: meta, isError: metaError } = useQuery({
    queryKey: ['meta-filters'],
    queryFn: fetchMetaFilters,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 2,
  })

  const tabs: Array<{ id: TabId; label: string; count?: number }> = [
    { id: 'immediate', label: 'Immediate' },
    { id: 'active', label: 'Active' },
    { id: 'low_priority', label: 'Past Deadline' },
    ...(isManager ? [{ id: 'manager' as TabId, label: 'Manager' }] : []),
  ]

  // Apply sidebar filters (no date tab cutoff — tabs handle that now)
  const sidebarFiltered = useMemo(() => {
    if (!dischargData?.records) return []

    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    const tomorrowStr = tomorrow.toISOString().slice(0, 10)

    return dischargData.records.filter(row => {
      // Exclude records with discharge dates far in the future (data entry errors)
      if (row.discharge_date > tomorrowStr) return false

      if (filters.practices.length > 0 && !filters.practices.includes(row.practice ?? '')) return false
      if (filters.payers.length > 0 && !filters.payers.includes(row.payer_name ?? '')) return false
      if (filters.lobNames.length > 0 && !filters.lobNames.includes(row.lob_name ?? '')) return false
      if (filters.stayTypes.length > 0 && !filters.stayTypes.includes(row.stay_type ?? '')) return false
      if (filters.dateFrom && row.discharge_date < filters.dateFrom) return false
      if (filters.dateTo && row.discharge_date > filters.dateTo) return false

      if (filters.assignee !== 'All') {
        const assigneePractices = meta?.assignees.find(a => a.name === filters.assignee)?.practices ?? []
        if (!assigneePractices.includes(row.practice ?? '')) return false
      }

      if (filters.outreachStatuses.length > 0 && !filters.outreachStatuses.includes(row.outreach_status)) return false

      return true
    })
  }, [dischargData, filters, meta])

  // Partition into queues, sorted by urgency (fewest days left first within Immediate/Active)
  const queues = useMemo(() => {
    const immediate: DischargeRecord[] = []
    const active: DischargeRecord[] = []
    const low_priority: DischargeRecord[] = []

    for (const row of sidebarFiltered) {
      const bucket = getQueueBucket(row)
      if (bucket === 'immediate') immediate.push(row)
      else if (bucket === 'active') active.push(row)
      else low_priority.push(row)
    }

    const byUrgency = (a: DischargeRecord, b: DischargeRecord) =>
      getDaysRemaining(a) - getDaysRemaining(b)

    immediate.sort(byUrgency)
    active.sort(byUrgency)

    return { immediate, active, low_priority }
  }, [sidebarFiltered])

  const tabCounts = {
    immediate: queues.immediate.length,
    active: queues.active.length,
    low_priority: queues.low_priority.length,
  }

  const filteredRows: DischargeRecord[] =
    activeTab === 'manager' ? [] :
    activeTab === 'immediate' ? queues.immediate :
    activeTab === 'active' ? queues.active :
    queues.low_priority

  // Pull latest version of selected row — search all records, not just current tab,
  // so the panel stays open even if a status save moves the record to a different queue.
  const effectiveSelectedRow = useMemo(() => {
    if (!selectedRow) return null
    const allRecords = dischargData?.records ?? []
    return allRecords.find(r =>
      r.event_id === selectedRow.event_id && r.discharge_date === selectedRow.discharge_date
    ) ?? null
  }, [selectedRow, dischargData])

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab)
    setSelectedRow(null)
  }

  const handleRowClick = (row: DischargeRecord) => {
    setSelectedRow(prev => (prev?.event_id === row.event_id ? null : row))
  }

  const handleSaveSuccess = (patientName: string) => {
    showToast(`Status updated for ${patientName}`, 'success')
  }

  const handleStatusToggle = (status: OutreachStatus) => {
    const current = filters.outreachStatuses
    const next = current.length === 1 && current[0] === status ? [] : [status]
    setFilter('outreachStatuses', next)
  }

  return (
    <>
      <AppShell
        sidebar={
          <Sidebar
            filters={
              <FilterSidebar
                meta={meta}
                metaError={metaError}
                filters={filters}
                onFilterChange={setFilter}
                onAssigneeChange={setAssignee}
              />
            }
            onClearFilters={clearAll}
            hasActiveFilters={hasActiveFilters}
          />
        }
      >
        <div className="flex flex-col gap-4">
          <AppHeader userName={user?.name} loadedAt={dischargData?.loaded_at} />

          {/* Tab strip */}
          <div
            className="inline-flex p-1 rounded-lg self-start"
            style={{ backgroundColor: '#e4eaf0' }}
            role="tablist"
            aria-label="Dashboard tabs"
          >
            {tabs.map(tab => {
              const isActive = activeTab === tab.id
              const count = tab.id !== 'manager' ? tabCounts[tab.id as keyof typeof tabCounts] : undefined
              const isImmediateUrgent = tab.id === 'immediate' && !isActive && (count ?? 0) > 0
              return (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={isActive}
                  aria-controls={`tabpanel-${tab.id}`}
                  onClick={() => handleTabChange(tab.id)}
                  className="inline-flex items-center gap-2 px-[18px] py-[6px] rounded-[7px] text-[13.5px] font-semibold transition-colors duration-100"
                  style={
                    isActive
                      ? { backgroundColor: '#132e45', color: '#ffffff' }
                      : isImmediateUrgent
                      ? { backgroundColor: 'transparent', color: '#1b4459', borderLeft: '3px solid #e53e3e', paddingLeft: '15px' }
                      : { backgroundColor: 'transparent', color: '#1b4459' }
                  }
                  onMouseEnter={e => {
                    if (!isActive)
                      (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'rgba(19,46,69,0.08)'
                  }}
                  onMouseLeave={e => {
                    if (!isActive)
                      (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent'
                  }}
                >
                  {tab.label}
                  {count !== undefined && (
                    <span
                      className="text-[11px] font-bold px-1.5 py-0.5 rounded-full"
                      style={
                        isActive
                          ? { backgroundColor: 'rgba(255,255,255,0.25)', color: '#fff' }
                          : isImmediateUrgent
                          ? { backgroundColor: '#fed7d7', color: '#c53030' }
                          : { backgroundColor: 'rgba(19,46,69,0.12)', color: '#1b4459' }
                      }
                    >
                      {count.toLocaleString()}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* Tab panel */}
          <div
            id={`tabpanel-${activeTab}`}
            role="tabpanel"
            aria-label={TAB_DESCRIPTIONS[activeTab]}
          >
            {activeTab === 'manager' ? (
              <ManagerDashboard />
            ) : (
              <>
                {/* Queue description */}
                <p className="text-[12px] text-text-muted mb-3">
                  {TAB_DESCRIPTIONS[activeTab]}
                </p>

                {/* Stat chips */}
                <StatChipRow records={filteredRows} />

                {/* Record count + title */}
                <div className="flex items-center gap-2 mt-3">
                  <h2 className="text-[16px] font-bold text-text-primary capitalize">
                    {TAB_LABELS[activeTab]}
                  </h2>
                  <span
                    className="px-2 py-0.5 rounded-full text-[12px] font-semibold text-white"
                    style={{ backgroundColor: '#132e45' }}
                  >
                    {filteredRows.length.toLocaleString()}
                  </span>
                </div>

                {/* Legend / filter */}
                <OutreachLegend
                  activeStatuses={filters.outreachStatuses}
                  onToggle={handleStatusToggle}
                />

                {/* Table + detail panel split layout */}
                <div className="flex gap-4 mt-2 overflow-x-hidden">
                  <div className={effectiveSelectedRow ? 'flex-1 min-w-0' : 'w-full'}>
                    <DischargeTable
                      data={filteredRows}
                      isLoading={dischargesLoading}
                      selectedRowId={effectiveSelectedRow?.event_id ?? null}
                      onRowClick={handleRowClick}
                    />
                  </div>

                  {effectiveSelectedRow && (
                    <div
                      className="w-[480px] shrink-0 flex flex-col"
                      style={{ height: 'calc(100vh - 380px)', minHeight: '300px' }}
                    >
                      <DetailPanel
                        row={effectiveSelectedRow}
                        onClose={() => setSelectedRow(null)}
                        onSaveSuccess={handleSaveSuccess}
                      />
                    </div>
                  )}
                </div>

                {/* Export button */}
                <div className="flex justify-start mt-2">
                  <button
                    onClick={() => exportToCsv(
                      filteredRows as unknown as Record<string, unknown>[],
                      CSV_COLUMNS,
                      `discharge_report_${fileTimestamp()}.csv`
                    )}
                    className="px-4 py-2 text-[13px] font-medium text-text-secondary rounded-md border border-border hover:border-navy hover:text-navy transition-colors"
                  >
                    Export CSV ({filteredRows.length.toLocaleString()} rows)
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </AppShell>

      <ToastContainer />
    </>
  )
}
