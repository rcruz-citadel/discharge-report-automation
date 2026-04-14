import { api } from './client'
import type { MetaFiltersResponse } from '../types/api'

export async function fetchMetaFilters(): Promise<MetaFiltersResponse> {
  const response = await api.get<MetaFiltersResponse>('/meta/filters')
  return response.data
}
