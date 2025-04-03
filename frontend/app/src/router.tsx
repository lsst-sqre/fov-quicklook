import { Navigate, Route, Routes } from 'react-router-dom'
import { Jobs } from './pages/admin/Jobs'
import { PodsStatus } from './pages/admin/PodStatus'
import { ConfigPage } from './pages/ConfigPage'
import { FItsHeaderPage } from './pages/FitsHeader'
import { Home } from './pages/Home'
import { Layout } from './pages/Layout'
import { CacheEntries } from './pages/admin/CacheEntries'
import { StorageExplorer } from './pages/admin/StorageExplorer'


export const AppRouter = () => (
  <Routes>
    <Route element={<Layout />}>
      <Route index element={<Navigate to="/visits" replace />} />
      <Route path="visits">
        <Route index element={<Home />} />
        <Route path=":visitId" element={<Home />} />
      </Route>
      <Route path="header/:visitId/:ccdName" element={<FItsHeaderPage />} />
      <Route path="config" element={<ConfigPage />} />
      <Route path="admin">
        <Route path="pod_status" element={<PodsStatus />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="cache-entries" element={<CacheEntries />} />
        <Route path="storage" element={<StorageExplorer />} />
      </Route>
    </Route>
  </Routes>
)
