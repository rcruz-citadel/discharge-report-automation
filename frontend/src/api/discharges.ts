import { api } from './client'
import type { DischargesResponse } from '../types/discharge'

export async function fetchDischarges(): Promise<DischargesResponse> {
  const response = await api.get<DischargesResponse>('/discharges')
  return response.data
}
