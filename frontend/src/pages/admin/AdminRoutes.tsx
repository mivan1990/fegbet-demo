import { Route, Routes } from 'react-router-dom'
import { AdminLayout } from '@/components/admin/AdminLayout'
import { NotFound } from '@/pages/NotFound'
import { AdminDashboard } from './AdminDashboard'
import { AdminGroups } from './AdminGroups'
import { AdminLogs } from './AdminLogs'
import { AdminMatches } from './AdminMatches'
import { AdminPlayers } from './AdminPlayers'
import { AdminSettings } from './AdminSettings'
import { AdminTeams } from './AdminTeams'
import { AdminUsers } from './AdminUsers'

export function AdminRoutes() {
  return (
    <Routes>
      <Route element={<AdminLayout />}>
        <Route index element={<AdminDashboard />} />
        <Route path="meciuri" element={<AdminMatches />} />
        <Route path="grupe" element={<AdminGroups />} />
        <Route path="echipe" element={<AdminTeams />} />
        <Route path="jucatori" element={<AdminPlayers />} />
        <Route path="utilizatori" element={<AdminUsers />} />
        <Route path="loguri" element={<AdminLogs />} />
        <Route path="setari" element={<AdminSettings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
