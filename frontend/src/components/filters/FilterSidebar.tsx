import type { MetaFiltersResponse } from '../../types/api'
import type { FilterState } from '../../types/api'
import { AssigneeSelect } from './AssigneeSelect'
import { PracticeMultiSelect } from './PracticeMultiSelect'
import { PayerMultiSelect } from './PayerMultiSelect'
import { LobMultiSelect } from './LobMultiSelect'
import { StayTypeMultiSelect } from './StayTypeMultiSelect'
import { DateRangePicker } from './DateRangePicker'

interface FilterSidebarProps {
  meta: MetaFiltersResponse | undefined
  metaError?: boolean
  filters: FilterState
  onFilterChange: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
}

/**
 * Sidebar filter controls. Each control fires immediately (no Apply button).
 * Assignee selection scopes the Practice options to that person's practices.
 * Spec: 5.5 Sidebar filter logic
 */
export function FilterSidebar({ meta, metaError, filters, onFilterChange }: FilterSidebarProps) {
  if (metaError) {
    return (
      <div
        className="flex flex-col gap-2 px-1 py-2 rounded-md"
        style={{ backgroundColor: 'rgba(229,62,62,0.12)', border: '1px solid rgba(229,62,62,0.3)' }}
      >
        <p className="text-[11px] font-semibold" style={{ color: '#fc8181' }}>
          Filter options unavailable
        </p>
        <p className="text-[10px]" style={{ color: '#feb2b2' }}>
          Could not load filter data. Reload the page to try again.
        </p>
      </div>
    )
  }

  if (!meta) {
    return (
      <div className="flex flex-col gap-4 px-1">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-8 skeleton rounded-md opacity-30" />
        ))}
      </div>
    )
  }

  // Scope practice options to the selected assignee's practices
  const availablePractices =
    filters.assignee !== 'All'
      ? (meta.assignees.find(a => a.name === filters.assignee)?.practices ?? meta.practices)
      : meta.practices

  return (
    <div className="flex flex-col gap-4">
      <AssigneeSelect
        assignees={meta.assignees}
        value={filters.assignee}
        onChange={v => {
          onFilterChange('assignee', v)
          // Clear practice filter when assignee changes (practices get re-scoped)
          onFilterChange('practices', [])
        }}
      />

      <PracticeMultiSelect
        options={availablePractices}
        value={filters.practices}
        onChange={v => onFilterChange('practices', v)}
      />

      <PayerMultiSelect
        options={meta.payers}
        value={filters.payers}
        onChange={v => onFilterChange('payers', v)}
      />

      <LobMultiSelect
        options={meta.lob_names}
        value={filters.lobNames}
        onChange={v => onFilterChange('lobNames', v)}
      />

      <StayTypeMultiSelect
        options={meta.stay_types}
        value={filters.stayTypes}
        onChange={v => onFilterChange('stayTypes', v)}
      />

      <DateRangePicker
        dateFrom={filters.dateFrom}
        dateTo={filters.dateTo}
        min={meta.discharge_date_min ?? undefined}
        max={meta.discharge_date_max ?? undefined}
        onChangeDateFrom={v => onFilterChange('dateFrom', v)}
        onChangeDateTo={v => onFilterChange('dateTo', v)}
      />
    </div>
  )
}
