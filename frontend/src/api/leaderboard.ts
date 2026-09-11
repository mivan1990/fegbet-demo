import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { LeaderboardRow } from './types'

export function useLeaderboard() {
  return useQuery({
    queryKey: ['leaderboard'],
    queryFn: async () => (await api.get<LeaderboardRow[]>('/leaderboard')).data,
  })
}
