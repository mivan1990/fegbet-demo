import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { AdminStats, AdminUser, LogFilters, LogPage, PointsMap } from './types'

export function useAdminStats() {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: async () => (await api.get<AdminStats>('/admin/stats')).data,
  })
}

// --------------------------------------------------------------------------- loguri
export function useAdminLogs(filters: LogFilters) {
  const params: Record<string, string | number> = {}
  if (filters.user_id) params.user_id = filters.user_id
  if (filters.action) params.action = filters.action
  if (filters.from) params.from = filters.from
  if (filters.to) params.to = filters.to
  if (filters.q) params.q = filters.q
  params.page = filters.page ?? 1

  return useQuery({
    queryKey: ['admin', 'logs', params],
    queryFn: async () => (await api.get<LogPage>('/admin/logs', { params })).data,
    placeholderData: (prev) => prev,
  })
}

// --------------------------------------------------------------------------- setari
export function useAdminSettings() {
  return useQuery({
    queryKey: ['admin', 'settings'],
    queryFn: async () => (await api.get<PointsMap>('/admin/settings')).data,
  })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (values: PointsMap) =>
      (await api.put<PointsMap>('/admin/settings', { values })).data,
    onSuccess: (data) => {
      qc.setQueryData(['admin', 'settings'], data)
      void qc.invalidateQueries({ queryKey: ['admin', 'logs'] })
      void qc.invalidateQueries({ queryKey: ['settings', 'points'] })
    },
  })
}

// ---------------------------------------------------------------------- utilizatori
export function useAdminUsers() {
  return useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => (await api.get<AdminUser[]>('/admin/users')).data,
  })
}

function invalidateUsers(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ['admin', 'users'] })
  void qc.invalidateQueries({ queryKey: ['admin', 'logs'] })
  void qc.invalidateQueries({ queryKey: ['leaderboard'] })
}

export function useSetUserPassword() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, new_password }: { id: number; new_password: string }) =>
      (await api.put<AdminUser>(`/admin/users/${id}/password`, { new_password })).data,
    onSuccess: () => invalidateUsers(qc),
  })
}

export function useSetUserRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, is_admin }: { id: number; is_admin: boolean }) =>
      (await api.put<AdminUser>(`/admin/users/${id}/role`, { is_admin })).data,
    onSuccess: () => invalidateUsers(qc),
  })
}

export function useSetUserActive() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) =>
      (await api.put<AdminUser>(`/admin/users/${id}/active`, { is_active })).data,
    onSuccess: () => invalidateUsers(qc),
  })
}
