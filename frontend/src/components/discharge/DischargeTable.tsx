import { useRef, useState, type KeyboardEvent } from 'react'
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import type { DischargeRecord } from '../../types/discharge'
import { OUTREACH_STATUS_COLORS } from '../../types/discharge'
import { dischargeColumns } from './DischargeTableColumns'

interface DischargeTableProps {
  data: DischargeRecord[]
  isLoading?: boolean
  selectedRowId: string | null
  onRowClick: (row: DischargeRecord) => void
}

/**
 * Virtualized discharge table using TanStack Table + Virtual.
 * Only ~20 DOM rows at any time regardless of dataset size (17k rows).
 * Spec: 4.6 Table Virtualization, 5.5 Discharge Table
 */
export function DischargeTable({ data, isLoading, selectedRowId, onRowClick }: DischargeTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'discharge_date', desc: true },
  ])

  const table = useReactTable({
    data,
    columns: dischargeColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: { sorting },
    onSortingChange: setSorting,
  })

  const rows = table.getRowModel().rows
  const tableContainerRef = useRef<HTMLDivElement>(null)

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => 40,
    overscan: 10,
  })

  const virtualRows = rowVirtualizer.getVirtualItems()
  const totalSize = rowVirtualizer.getTotalSize()
  const paddingTop = virtualRows.length > 0 ? virtualRows[0].start : 0
  const paddingBottom =
    virtualRows.length > 0 ? totalSize - (virtualRows[virtualRows.length - 1].end ?? totalSize) : 0

  if (isLoading) {
    return (
      <div className="bg-surface rounded-lg shadow-card overflow-hidden">
        {/* Header skeleton */}
        <div className="px-3 py-[10px] grid" style={{ gridTemplateColumns: '180px 120px 160px 150px 180px 80px 130px 160px', backgroundColor: '#132e45' }}>
          {['Patient Name', 'Discharge Date', 'Practice', 'Payer', 'Hospital', 'LOS', 'Disposition', 'Status'].map(h => (
            <div key={h} className="text-[11px] font-semibold uppercase" style={{ color: '#ffffff' }}>{h}</div>
          ))}
        </div>
        {/* Skeleton rows */}
        <div className="divide-y divide-border-light">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="px-3 py-[9px] flex gap-3 items-center">
              <div className="skeleton h-4 flex-1 rounded" />
              <div className="skeleton h-4 w-24 rounded" />
              <div className="skeleton h-4 w-32 rounded" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="bg-surface rounded-lg shadow-card p-12 flex flex-col items-center gap-3">
        <svg className="w-12 h-12 text-text-light" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <p className="text-[16px] font-bold text-text-primary">No records match the current filters</p>
        <p className="text-[13px] text-text-muted">Try adjusting or clearing the filters to see results.</p>
      </div>
    )
  }

  return (
    <div
      ref={tableContainerRef}
      className="bg-surface rounded-lg shadow-card overflow-auto"
      style={{
        height: 'calc(100vh - 380px)',
        minHeight: '300px',
      }}
      role="grid"
      aria-label="Discharge records"
      aria-rowcount={data.length}
    >
      <table className="w-full border-collapse" style={{ tableLayout: 'fixed' }}>
        <colgroup>
          {table.getAllColumns().map(col => (
            <col key={col.id} style={{ width: col.getSize() }} />
          ))}
        </colgroup>

        {/* Sticky header */}
        <thead className="sticky top-0 z-10">
          {table.getHeaderGroups().map(headerGroup => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map(header => {
                const isSorted = header.column.getIsSorted()
                const canSort = header.column.getCanSort()
                const align = (header.column.columnDef.meta as { align?: string } | undefined)?.align

                return (
                  <th
                    key={header.id}
                    onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                    className="text-[11px] font-semibold uppercase px-3 py-[10px] select-none whitespace-nowrap overflow-hidden text-ellipsis tracking-wider"
                    style={{
                      backgroundColor: '#132e45',
                      color: '#ffffff',
                      textAlign: align === 'right' ? 'right' : 'left',
                      cursor: canSort ? 'pointer' : 'default',
                      borderBottom: '2px solid #1b4459',
                      letterSpacing: '0.04em',
                    }}
                    aria-sort={isSorted === 'asc' ? 'ascending' : isSorted === 'desc' ? 'descending' : 'none'}
                  >
                    <span className="inline-flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {isSorted === 'asc' && <span style={{ color: '#a8c4d8' }}> ↑</span>}
                      {isSorted === 'desc' && <span style={{ color: '#a8c4d8' }}> ↓</span>}
                      {!isSorted && canSort && <span className="opacity-30" style={{ color: '#a8c4d8' }}> ↕</span>}
                    </span>
                  </th>
                )
              })}
            </tr>
          ))}
        </thead>

        <tbody>
          {paddingTop > 0 && (
            <tr>
              <td style={{ height: paddingTop }} colSpan={dischargeColumns.length} />
            </tr>
          )}

          {virtualRows.map(virtualRow => {
            const row = rows[virtualRow.index]
            const isSelected = row.original.event_id === selectedRowId
            const statusColors = OUTREACH_STATUS_COLORS[row.original.outreach_status]
            const isEven = virtualRow.index % 2 === 0

            // Row background priority: selected > status tint > alternating stripe
            const rowBg = isSelected
              ? '#e8f0f7'
              : statusColors.rowTint !== 'transparent'
              ? statusColors.rowTint
              : isEven
              ? '#ffffff'
              : '#f8fafb'

            return (
              <tr
                key={row.id}
                onClick={() => onRowClick(row.original)}
                onKeyDown={(e: KeyboardEvent) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onRowClick(row.original)
                  }
                }}
                tabIndex={0}
                aria-rowindex={virtualRow.index + 1}
                aria-selected={isSelected}
                className="cursor-pointer transition-colors duration-100 outline-none focus-visible:ring-2 focus-visible:ring-orange focus-visible:ring-inset"
                style={{
                  backgroundColor: rowBg,
                  borderLeft: isSelected ? '3px solid #132e45' : undefined,
                  height: 40,
                }}
                onMouseEnter={e => {
                  if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.backgroundColor = '#edf2f7'
                }}
                onMouseLeave={e => {
                  if (!isSelected)
                    (e.currentTarget as HTMLTableRowElement).style.backgroundColor = rowBg
                }}
              >
                {row.getVisibleCells().map(cell => {
                  const align = (cell.column.columnDef.meta as { align?: string } | undefined)?.align
                  return (
                    <td
                      key={cell.id}
                      className="text-[13px] px-3 py-[9px] overflow-hidden text-ellipsis whitespace-nowrap"
                      style={{
                        textAlign: align === 'right' ? 'right' : 'left',
                        color: '#2a3f50',
                        borderBottom: '1px solid #e8ecf0',
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  )
                })}
              </tr>
            )
          })}

          {paddingBottom > 0 && (
            <tr>
              <td style={{ height: paddingBottom }} colSpan={dischargeColumns.length} />
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
