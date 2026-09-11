import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { Player, PlayerInput } from './types'

const keys = {
  public: ['players'] as const,
  admin: ['admin', 'players'] as const,
}

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: keys.public })
  void qc.invalidateQueries({ queryKey: keys.admin })
  void qc.invalidateQueries({ queryKey: ['admin', 'stats'] })
}

export function usePlayers() {
  return useQuery({
    queryKey: keys.public,
    queryFn: async () => (await api.get<Player[]>('/players')).data,
  })
}

export function useAdminPlayers() {
  return useQuery({
    queryKey: keys.admin,
    queryFn: async () => (await api.get<Player[]>('/admin/players')).data,
  })
}

export function useCreatePlayer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: PlayerInput) => (await api.post<Player>('/admin/players', body)).data,
    onSuccess: () => invalidate(qc),
  })
}

export function useUpdatePlayer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Partial<PlayerInput> }) =>
      (await api.put<Player>(`/admin/players/${id}`, body)).data,
    onSuccess: () => invalidate(qc),
  })
}

export function useDeletePlayer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.delete<{ ok: boolean; mode: 'soft' | 'hard'; detail?: string }>(
        `/admin/players/${id}`,
      )).data,
    onSuccess: () => invalidate(qc),
  })
}
