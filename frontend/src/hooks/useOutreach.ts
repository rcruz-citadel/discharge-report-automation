import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { upsertOutreach, fetchAttempts, logAttempt } from '../api/outreach'
import type { OutreachRecord, OutreachUpsertPayload, OutreachAttempt, LogAttemptResponse } from '../types/discharge'
import { DISCHARGES_QUERY_KEY } from './useDischarges'

/**
 * Mutation hook for upserting outreach status.
 *
 * On success: invalidates the discharges query to trigger a background refetch.
 * The table row updates optimistically (caller handles optimistic update).
 */
export function useUpsertOutreach() {
  const queryClient = useQueryClient()

  return useMutation<OutreachRecord, Error, OutreachUpsertPayload>({
    mutationFn: upsertOutreach,
    onSuccess: (_data, variables) => {
      // Immediately patch the cached row so the table updates without waiting for a refetch
      queryClient.setQueryData(DISCHARGES_QUERY_KEY, (old: { records: OutreachUpsertPayload[] } | undefined) => {
        if (!old) return old
        return {
          ...old,
          records: old.records.map((r: { event_id: string; discharge_date: string; outreach_status?: string; outreach_notes?: string }) =>
            r.event_id === variables.event_id && r.discharge_date === variables.discharge_date
              ? { ...r, outreach_status: variables.status, outreach_notes: variables.notes }
              : r
          ),
        }
      })
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attempts', eventId, dischargeDate] })
    },
  })
}
