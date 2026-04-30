import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { upsertOutreach, fetchAttempts, logAttempt } from '../api/outreach'
import type { OutreachRecord, OutreachUpsertPayload, OutreachAttempt, LogAttemptResponse } from '../types/discharge'
import { DISCHARGES_QUERY_KEY } from './useDischarges'

export function useUpsertOutreach() {
  const queryClient = useQueryClient()

  return useMutation<OutreachRecord, Error, OutreachUpsertPayload>({
    mutationFn: upsertOutreach,
    onSuccess: (_data, variables) => {
      // Optimistic patch for immediate UI feedback
      queryClient.setQueryData(DISCHARGES_QUERY_KEY, (old: { records: OutreachUpsertPayload[] } | undefined) => {
        if (!old) return old
        return {
          ...old,
          records: old.records.map((r: {
            event_id: string
            discharge_date: string
            outreach_status?: string
            outreach_notes?: string
            discharge_summary_dropped?: boolean
          }) =>
            r.event_id === variables.event_id && r.discharge_date === variables.discharge_date
              ? {
                  ...r,
                  outreach_status: variables.status,
                  outreach_notes: variables.notes,
                  discharge_summary_dropped: variables.discharge_summary_dropped,
                }
              : r
          ),
        }
      })
      // Background refetch to confirm the save persisted in the DB
      queryClient.invalidateQueries({ queryKey: DISCHARGES_QUERY_KEY })
    },
  })
}

export function useAttempts(eventId: string, dischargeDate: string) {
  return useQuery<OutreachAttempt[]>({
    queryKey: ['attempts', eventId, dischargeDate],
    queryFn: () => fetchAttempts(eventId, dischargeDate),
    staleTime: 30_000,
  })
}

export function useLogAttempt(eventId: string, dischargeDate: string) {
  const queryClient = useQueryClient()
  return useMutation<LogAttemptResponse, Error>({
    mutationFn: () => logAttempt(eventId, dischargeDate),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['attempts', eventId, dischargeDate] })
      // If 3rd attempt auto-completed the record, patch the cache immediately
      if (data.auto_completed) {
        queryClient.setQueryData(DISCHARGES_QUERY_KEY, (old: { records: { event_id: string; discharge_date: string; outreach_status?: string }[] } | undefined) => {
          if (!old) return old
          return {
            ...old,
            records: old.records.map(r =>
              r.event_id === eventId && r.discharge_date === dischargeDate
                ? { ...r, outreach_status: 'outreach_complete' }
                : r
            ),
          }
        })
      }
      // Background refetch to sync discharge state (attempt count + auto-complete status)
      queryClient.invalidateQueries({ queryKey: DISCHARGES_QUERY_KEY })
    },
  })
}
