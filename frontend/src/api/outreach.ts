import { api } from './client'
import type { OutreachRecord, OutreachUpsertPayload, OutreachAttempt, LogAttemptResponse } from '../types/discharge'

export async function fetchOutreach(eventId: string, dischargeDate: string): Promise<OutreachRecord | null> {
  try {
    const response = await api.get<OutreachRecord>(`/outreach/${eventId}`, {
      params: { discharge_date: dischargeDate },
    })
    return response.data
  } catch (error: unknown) {
    // 404 means no outreach record exists — that's valid (means no_outreach)
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null
    }
    throw error
  }
}

export async function upsertOutreach(payload: OutreachUpsertPayload): Promise<OutreachRecord> {
  const response = await api.put<OutreachRecord>(`/outreach/${payload.event_id}`, {
    discharge_date: payload.discharge_date,
    status: payload.status,
    notes: payload.notes,
    discharge_summary_dropped: payload.discharge_summary_dropped,
  })
  return response.data
}

// Need axios import for isAxiosError
import axios from 'axios'

export async function fetchAttempts(eventId: string, dischargeDate: string): Promise<OutreachAttempt[]> {
  const response = await api.get<OutreachAttempt[]>(`/outreach/${eventId}/attempts`, {
    params: { discharge_date: dischargeDate },
  })
  return response.data
}

export async function logAttempt(eventId: string, dischargeDate: string): Promise<LogAttemptResponse> {
  const response = await api.post<LogAttemptResponse>(`/outreach/${eventId}/attempts`, null, {
    params: { discharge_date: dischargeDate },
  })
  return response.data
}
