import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, getToken } from './client'
import type { Group, GroupPrediction, Match } from './types'

const keys = {
  public: ['groups'] as const,
  detail: (id: number) => ['groups', id] as const,
  mine: ['group-predictions', 'mine'] as const,
  admin: ['admin', 'groups'] as const,
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: keys.public })
  void qc.invalidateQueries({ queryKey: keys.mine })
  void qc.invalidateQueries({ queryKey: keys.admin })
}

// -------------------------------------------------------------------------- public
export function useGroups() {
  return useQuery({
    queryKey: keys.public,
    queryFn: async () => (await api.get<Group[]>('/groups')).data,
  })
}

export function useGroup(id: number) {
  return useQuery({
    queryKey: keys.detail(id),
    queryFn: async () => (await api.get<Group>(`/groups/${id}`)).data,
    enabled: Number.isFinite(id),
  })
}

export function useMyGroupPredictions() {
  return useQuery({
    queryKey: keys.mine,
    queryFn: async () => (await api.get<GroupPrediction[]>('/group-predictions/mine')).data,
    // Fara token nu are rost sa ceara — la fel ca la bilete.
    enabled: !!getToken(),
  })
}

export function useSaveGroupPrediction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      groupId,
      predictionId,
      teamIds,
    }: {
      groupId: number
      /** null = creeaza un pronostic nou; altfel actualizeaza pronosticul existent. */
      predictionId: number | null
      teamIds: number[]
    }) =>
      predictionId
        ? (
            await api.put<GroupPrediction>(`/group-predictions/${predictionId}`, {
              team_ids: teamIds,
            })
          ).data
        : (
            await api.post<GroupPrediction>('/group-predictions', {
              group_id: groupId,
              team_ids: teamIds,
            })
          ).data,
    onSuccess: (_data, vars) => {
      invalidateAll(qc)
      void qc.invalidateQueries({ queryKey: keys.detail(vars.groupId) })
    },
  })
}

export function useDeleteGroupPrediction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/group-predictions/${id}`)).data,
    onSuccess: () => invalidateAll(qc),
  })
}

// --------------------------------------------------------------------------- admin
export function useAdminGroups() {
  return useQuery({
    queryKey: keys.admin,
    queryFn: async () => (await api.get<Group[]>('/admin/groups')).data,
  })
}

export interface GroupSpecInput {
  name: string
  team_ids: number[]
}

function invalidateAfterRosterChange(qc: ReturnType<typeof useQueryClient>) {
  invalidateAll(qc)
  void qc.invalidateQueries({ queryKey: ['matches'] })
  void qc.invalidateQueries({ queryKey: ['admin', 'matches'] })
  void qc.invalidateQueries({ queryKey: ['bracket'] })
  void qc.invalidateQueries({ queryKey: ['teams'] })
  void qc.invalidateQueries({ queryKey: ['admin', 'teams'] })
}

export function useGenerateGroups() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (groups: GroupSpecInput[]) =>
      (await api.post<Group[]>('/admin/groups/generate', { groups })).data,
    onSuccess: () => invalidateAfterRosterChange(qc),
  })
}

export interface GroupUpdateInput {
  name?: string
  qualifiers_count?: number
  team_ids?: number[]
}

export function useUpdateGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: GroupUpdateInput }) =>
      (await api.put<Group>(`/admin/groups/${id}`, body)).data,
    onSuccess: () => invalidateAfterRosterChange(qc),
  })
}

export function useDeleteGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/admin/groups/${id}`)).data,
    onSuccess: () => invalidateAfterRosterChange(qc),
  })
}

export function useFinalizeGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, teamIds }: { id: number; teamIds?: number[] }) =>
      (
        await api.post<Group>(
          `/admin/groups/${id}/finalize`,
          teamIds ? { team_ids: teamIds } : {},
        )
      ).data,
    onSuccess: () => {
      invalidateAll(qc)
      void qc.invalidateQueries({ queryKey: ['leaderboard'] })
      void qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })
}

export function useGenerateBracketFromGroups() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () =>
      (await api.post<Match[]>('/admin/bracket/generate-from-groups')).data,
    onSuccess: () => {
      invalidateAll(qc)
      void qc.invalidateQueries({ queryKey: ['matches'] })
      void qc.invalidateQueries({ queryKey: ['bracket'] })
      void qc.invalidateQueries({ queryKey: ['admin', 'matches'] })
    },
  })
}
