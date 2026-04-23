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
    onSuccess: () => {
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attempts', eventId, dischargeDate] })
    },
  })
}
