import { useQuery } from '@tanstack/react-query'
import { fetchDischarges } from '../api/discharges'
import type { DischargesResponse } from '../types/discharge'

export const DISCHARGES_QUERY_KEY = ['discharges'] as const

/**
 * Fetch all discharge records merged with outreach status.
 *
 * staleTime: 5 min — matches Streamlit V2's ttl=300 behavior.
 * After any outreach upsert, queryClient.invalidateQueries triggers background refetch.
 */
export function useDischarges() {
  return useQuery<DischargesResponse>({
    queryKey: DISCHARGES_QUERY_KEY,
    queryFn: fetchDischarges,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })
}
