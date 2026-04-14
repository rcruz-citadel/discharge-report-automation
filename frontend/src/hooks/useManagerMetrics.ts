import { useQuery } from '@tanstack/react-query'
import { fetchManagerMetrics } from '../api/manager'
import type { ManagerMetricsResponse } from '../types/api'

export const MANAGER_METRICS_QUERY_KEY = ['manager-metrics'] as const

export function useManagerMetrics(enabled: boolean = true) {
  return useQuery<ManagerMetricsResponse>({
    queryKey: MANAGER_METRICS_QUERY_KEY,
    queryFn: fetchManagerMetrics,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    enabled,
  })
}
