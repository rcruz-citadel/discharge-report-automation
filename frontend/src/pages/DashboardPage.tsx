import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { DischargeRecord } from '../types/discharge'
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

type TabId = 'recent' | 'sixMonths' | 'all' | 'manager'

const CSV_COLUMNS = [
  'patient_name', 'birth_date', 'insurance_member_id', 'phone',
  'discharge_date', 'admit_date', 'practice', 'payer_name',
  'lob_name', 'stay_type', 'discharge_hospital', 'length_of_stay',
  'disposition', 'dx_code', 'description',
  'patient_address', 'city', 'zip_code', 'state',
  'outreach_status', 'outreach_notes', 'outreach_updated_by',
]

/**
 * Main dashboard page. Orchestrates tabs, filters, table, detail panel.
 * Spec: 4 Agent 3 Frontend, 4.3 State Management, 4.12 Interaction Patterns
 */
export function DashboardPage() {
  const { user, isManager } = useAuth()
  const { filters, setFilter, clearAll, hasActiveFilters } = useFilters()
  const [activeTab, setActiveTab] = useState<TabId>('recent')
  const [selectedRow, setSelectedRow] = useState<DischargeRecord | null>(null)
  const { show: showToast, ToastContainer } = useToast()

  const { data: dischargData, isLoading: dischargesLoading } = useDischarges()
  const { data: meta } = useQuery({
    queryKey: ['meta-filters'],
    queryFn: fetchMetaFilters,
    staleTime: 5 * 60 * 1000,
  })

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: 'recent', label: 'Recent' },
    { id: 'sixMonths', label: 'Last 6 Months' },
    { id: 'all', label: 'All Discharges' },
    ...(isManager ? [{ id: 'manager' as TabId, label: 'Manager' }] : []),
  ]

  // Date cutoffs for tabs
  const now = new Date()
  const recentCutoff = new Date(now)
  recentCutoff.setDate(recentCutoff.getDate() - 30)
  const sixMonthCutoff = new Date(now)
  sixMonthCutoff.setMonth(sixMonthCutoff.getMonth() - 6)

  // Apply tab date filter + sidebar filters
  const filteredRows = useMemo(() => {
    if (!dischargData?.records) return []

    return dischargData.records.filter(row => {
      // Tab date filter
      const dischargeDate = new Date(row.discharge_date)
      if (activeTab === 'recent' && dischargeDate < recentCutoff) return false
      if (activeTab === 'sixMonths' && dischargeDate < sixMonthCutoff) return false

      // Sidebar filters
      if (filters.practices.length > 0 && !filters.practices.includes(row.practice ?? '')) return false
      if (filters.payers.length > 0 && !filters.payers.includes(row.payer_name ?? '')) return false
      if (filters.lobNames.length > 0 && !filters.lobNames.includes(row.lob_name ?? '')) return false
      if (filters.stayTypes.length > 0 && !filters.stayTypes.includes(row.stay_type ?? '')) return false
      if (filters.dateFrom && row.discharge_date < filters.dateFrom) return false
      if (filters.dateTo && row.discharge_date > filters.dateTo) return false

      // Assignee filter: scope to that person's practices
      if (filters.assignee !== 'All') {
        const assigneePractices = meta?.assignees.find(a => a.name === filters.assignee)?.practices ?? []
        if (!assigneePractices.includes(row.practice ?? '')) return false
      }

      return true
    })
  }, [dischargData, activeTab, filters, meta, recentCutoff, sixMonthCutoff])

  // If the selected row is no longer in filtered results, close the panel
  const effectiveSelectedRow = useMemo(() => {
    if (!selectedRow) return null
    const stillVisible = filteredRows.some(r => r.event_id === selectedRow.event_id)
    return stillVisible ? selectedRow : null
  }, [selectedRow, filteredRows])

  // Sync effectiveSelectedRow back to state
  if (effectiveSelectedRow !== selectedRow && selectedRow !== null) {
    setSelectedRow(effectiveSelectedRow)
  }

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab)
    setSelectedRow(null)
  }

  const handleRowClick = (row: DischargeRecord) => {
    setSelectedRow(prev => (prev?.event_id === row.event_id ? null : row))
  }

  const handleSaveSuccess = (patientName: string) => {
    showToast(`Status updated for ${patientName}`, 'success')
    setSelectedRow(null)
  }

  const tabLabels: Record<TabId, string> = {
    recent: 'Recent (30 Days)',
    sixMonths: 'Last 6 Months',
    all: 'All Discharges',
    manager: 'Manager Dashboard',
  }

  return (
    <>
      <AppShell
        sidebar={
          <Sidebar
            filters={
              <FilterSidebar
                meta={meta}
                filters={filters}
                onFilterChange={setFilter}
              />
            }
            onClearFilters={clearAll}
            hasActiveFilters={hasActiveFilters}
          />
        }
      >
        <div className="flex flex-col gap-4">
          {/* Header: logo row + banner */}
          <AppHeader userName={user?.name} />

          {/* Tab strip */}
          <div
            className="inline-flex p-1 rounded-lg self-start"
            style={{ backgroundColor: '#e4eaf0' }}
            role="tablist"
            aria-label="Dashboard tabs"
          >
            {tabs.map(tab => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`tabpanel-${tab.id}`}
                onClick={() => handleTabChange(tab.id)}
                className="px-[18px] py-[6px] rounded-[7px] text-[13.5px] font-semibold transition-colors duration-100"
                style={{
                  backgroundColor: activeTab === tab.id ? '#132e45' : 'transparent',
                  color: activeTab === tab.id ? '#ffffff' : '#1b4459',
                }}
                onMouseEnter={e => {
                  if (activeTab !== tab.id)
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'rgba(19,46,69,0.08)'
                }}
                onMouseLeave={e => {
                  if (activeTab !== tab.id)
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab panel */}
          <div
            id={`tabpanel-${activeTab}`}
            role="tabpanel"
            aria-label={tabLabels[activeTab]}
          >
            {activeTab === 'manager' ? (
              <ManagerDashboard />
            ) : (
              <>
                {/* Stat chips */}
                <StatChipRow records={filteredRows} />

                {/* Record count badge */}
                <div className="flex items-center gap-2 mt-3">
                  <h2 className="text-[16px] font-bold text-text-primary">{tabLabels[activeTab]}</h2>
                  <span
                    className="px-2 py-0.5 rounded-full text-[12px] font-semibold text-white"
                    style={{ backgroundColor: '#132e45' }}
                  >
                    {filteredRows.length.toLocaleString()}
                  </span>
                </div>

                {/* Legend */}
                <OutreachLegend />

                {/* Table + detail panel split layout */}
                <div className="flex gap-4 mt-2">
                  <div className={effectiveSelectedRow ? 'flex-1 min-w-0' : 'w-full'}>
                    <DischargeTable
                      data={filteredRows}
                      isLoading={dischargesLoading}
                      selectedRowId={effectiveSelectedRow?.event_id ?? null}
                      onRowClick={handleRowClick}
                    />
                  </div>

                  {effectiveSelectedRow && (
                    <div className="w-[480px] shrink-0">
                      <DetailPanel
                        row={effectiveSelectedRow}
                        onClose={() => setSelectedRow(null)}
                        onSaveSuccess={handleSaveSuccess}
                      />
                    </div>
                  )}
                </div>

                {/* Export button */}
                <div className="flex justify-end mt-2">
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
