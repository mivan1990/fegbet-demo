import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { BracketRound, Match, MatchDetail } from './types'

export interface SettlePayload {
  home_score: number
  away_score: number
  penalties_home?: number | null
  penalties_away?: number | null
  scorers: { player_id: number; goals: number }[]
}

export interface SettleResult {
  match: MatchDetail
  tickets_settled: number
  warning: string | null
}

const keys = {
  publicList: ['matches'] as const,
  bracket: ['bracket'] as const,
  adminList: ['admin', 'matches'] as const,
  detail: (id: number) => ['matches', id] as const,
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ['matches'] })
  void qc.invalidateQueries({ queryKey: keys.bracket })
  void qc.invalidateQueries({ queryKey: keys.adminList })
  void qc.invalidateQueries({ queryKey: ['admin', 'stats'] })
}

export function useMatches() {
  return useQuery({
    queryKey: keys.publicList,
    queryFn: async () => (await api.get<Match[]>('/matches')).data,
  })
}

export function useMatch(id: number) {
  return useQuery({
    queryKey: keys.detail(id),
    queryFn: async () => (await api.get<MatchDetail>(`/matches/${id}`)).data,
    enabled: Number.isFinite(id),
  })
}

export function useBracket() {
  return useQuery({
    queryKey: keys.bracket,
    queryFn: async () => (await api.get<BracketRound[]>('/bracket')).data,
  })
}

export function useAdminMatches() {
  return useQuery({
    queryKey: keys.adminList,
    queryFn: async () => (await api.get<Match[]>('/admin/matches')).data,
  })
}

export interface MatchInput {
  round_no: number
  bracket_position: number
  stage_label?: string | null
  home_team_id?: number | null
  away_team_id?: number | null
  scheduled_at?: string | null
}

export function useCreateMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: MatchInput) => (await api.post<Match>('/admin/matches', body)).data,
    onSuccess: () => invalidateAll(qc),
  })
}

export function useUpdateMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Partial<MatchInput> & { status?: string } }) =>
      (await api.put<Match>(`/admin/matches/${id}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  })
}

export function useDeleteMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/admin/matches/${id}`)).data,
    onSuccess: () => invalidateAll(qc),
  })
}

export function useScheduleMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, scheduled_at }: { id: number; scheduled_at: string | null }) =>
      (await api.put<Match>(`/admin/matches/${id}/schedule`, { scheduled_at })).data,
    onSuccess: () => invalidateAll(qc),
  })
}

export function useGenerateBracket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ size, team_ids }: { size: number; team_ids: number[] }) =>
      (await api.post<Match[]>('/admin/bracket/generate', { size, team_ids })).data,
    onSuccess: () => invalidateAll(qc),
  })
}

export function useSettleMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: SettlePayload }) =>
      (await api.post<SettleResult>(`/admin/matches/${id}/settle`, body)).data,
    onSuccess: () => {
      invalidateAll(qc)
      void qc.invalidateQueries({ queryKey: ['tickets'] })
      void qc.invalidateQueries({ queryKey: ['leaderboard'] })
      void qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })
}
