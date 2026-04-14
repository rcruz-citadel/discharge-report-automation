import { useMutation, useQueryClient } from '@tanstack/react-query'
import { upsertOutreach } from '../api/outreach'
import type { OutreachRecord, OutreachUpsertPayload } from '../types/discharge'
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
