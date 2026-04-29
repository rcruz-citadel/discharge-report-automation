import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { FilterState } from '../types/api'
import type { OutreachStatus } from '../types/discharge'

const DEFAULT_FILTERS: FilterState = {
  assignee: 'All',
  practices: [],
  payers: [],
  lobNames: [],
  stayTypes: [],
  dateFrom: null,
  dateTo: null,
  outreachStatuses: [],
}

/**
 * Filter state stored in URL search params.
 *
 * Shareable (copy URL to share exact filter state) and survives page refresh.
 * Tab state is NOT in URL (it's transient UI state in DashboardPage).
 */
export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  const filters: FilterState = {
    assignee: searchParams.get('assignee') ?? DEFAULT_FILTERS.assignee,
    practices: searchParams.getAll('practice'),
    payers: searchParams.getAll('payer'),
    lobNames: searchParams.getAll('lob'),
    stayTypes: searchParams.getAll('stayType'),
    dateFrom: searchParams.get('dateFrom') ?? null,
    dateTo: searchParams.get('dateTo') ?? null,
    outreachStatuses: searchParams.getAll('outreachStatus') as OutreachStatus[],
  }

  // Dedicated setter: changes assignee AND clears practices in one navigation so
  // the two setSearchParams calls don't race and overwrite each other.
  const setAssignee = useCallback(
    (name: string) => {
      setSearchParams(
        prev => {
          const next = new URLSearchParams(prev)
          if (name === 'All' || !name) {
            next.delete('assignee')
          } else {
            next.set('assignee', name)
          }
          next.delete('practice')
          return next
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )

  const setFilter = useCallback(
    <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
      setSearchParams(
        prev => {
          const next = new URLSearchParams(prev)

          switch (key) {
            case 'assignee':
              if (value === 'All' || !value) {
                next.delete('assignee')
              } else {
                next.set('assignee', value as string)
              }
              break

            case 'practices':
              next.delete('practice')
              ;(value as string[]).forEach(v => next.append('practice', v))
              break

            case 'payers':
              next.delete('payer')
              ;(value as string[]).forEach(v => next.append('payer', v))
              break

            case 'lobNames':
              next.delete('lob')
              ;(value as string[]).forEach(v => next.append('lob', v))
              break

            case 'stayTypes':
              next.delete('stayType')
              ;(value as string[]).forEach(v => next.append('stayType', v))
              break

            case 'dateFrom':
              if (!value) next.delete('dateFrom')
              else next.set('dateFrom', value as string)
              break

            case 'dateTo':
              if (!value) next.delete('dateTo')
              else next.set('dateTo', value as string)
              break

            case 'outreachStatuses':
              next.delete('outreachStatus')
              ;(value as string[]).forEach(v => next.append('outreachStatus', v))
              break
          }

          return next
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )

  const clearAll = useCallback(() => {
    setSearchParams({}, { replace: true })
  }, [setSearchParams])

  const hasActiveFilters =
    filters.assignee !== 'All' ||
    filters.practices.length > 0 ||
    filters.payers.length > 0 ||
    filters.lobNames.length > 0 ||
    filters.stayTypes.length > 0 ||
    filters.dateFrom !== null ||
    filters.dateTo !== null ||
    filters.outreachStatuses.length > 0

  return { filters, setFilter, setAssignee, clearAll, hasActiveFilters }
}
