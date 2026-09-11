import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getToken } from './client'
import type { PointsMap, SelectionInput, Ticket } from './types'

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ['tickets'] })
  void qc.invalidateQueries({ queryKey: ['matches'] })
  void qc.invalidateQueries({ queryKey: ['leaderboard'] })
}

export function usePointsSettings() {
  return useQuery({
    queryKey: ['settings', 'points'],
    queryFn: async () => (await api.get<PointsMap>('/settings/points')).data,
    staleTime: 5 * 60 * 1000,
  })
}

export function useMyTickets() {
  return useQuery({
    queryKey: ['tickets', 'mine'],
    queryFn: async () => (await api.get<Ticket[]>('/tickets/mine')).data,
    // Fara token nu are rost sa ceara — si un 401 ar declansa „sesiune expirata".
    enabled: !!getToken(),
  })
}

export function useSaveTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ matchId, selections }: { matchId: number; selections: SelectionInput[] }) =>
      (await api.post<Ticket>('/tickets', { match_id: matchId, selections })).data,
    onSuccess: () => invalidate(qc),
  })
}

export function useUpdateTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, selections }: { id: number; selections: SelectionInput[] }) =>
      (await api.put<Ticket>(`/tickets/${id}`, { selections })).data,
    onSuccess: () => invalidate(qc),
  })
}

export function useDeleteTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/tickets/${id}`)).data,
    onSuccess: () => invalidate(qc),
  })
}
