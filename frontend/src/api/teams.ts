import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { Team, TeamAdmin, TeamInput } from './types'

const keys = {
  public: ['teams'] as const,
  admin: ['admin', 'teams'] as const,
}

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: keys.public })
  void qc.invalidateQueries({ queryKey: keys.admin })
  void qc.invalidateQueries({ queryKey: ['admin', 'stats'] })
}

export function useTeams() {
  return useQuery({
    queryKey: keys.public,
    queryFn: async () => (await api.get<Team[]>('/teams')).data,
  })
}

export function useAdminTeams() {
  return useQuery({
    queryKey: keys.admin,
    queryFn: async () => (await api.get<TeamAdmin[]>('/admin/teams')).data,
  })
}

export function useCreateTeam() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: TeamInput) => (await api.post<Team>('/admin/teams', body)).data,
    onSuccess: () => invalidate(qc),
  })
}

export function useUpdateTeam() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Partial<TeamInput> }) =>
      (await api.put<Team>(`/admin/teams/${id}`, body)).data,
    onSuccess: () => invalidate(qc),
  })
}

export function useDeleteTeam() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/admin/teams/${id}`)).data,
    onSuccess: () => invalidate(qc),
  })
}
