import { api } from './client'
import type { ManagerMetricsResponse } from '../types/api'

export async function fetchManagerMetrics(): Promise<ManagerMetricsResponse> {
  const response = await api.get<ManagerMetricsResponse>('/manager/metrics')
  return response.data
}
