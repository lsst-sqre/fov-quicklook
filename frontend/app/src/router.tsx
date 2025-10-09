import { useStore } from 'react-redux'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useHashSync } from './hooks/useHashSync'
import { ConfigPage } from './pages/ConfigPage'
import { FItsHeaderPage } from './pages/FitsHeader'
import { Home } from './pages/Home'
import { Layout } from './pages/Layout'
import { AppStore } from './store'
import { Dev } from './pages/Dev'
import { CacheEntries } from './pages/admin/CacheEntries'
import { StorageExplorer } from './pages/admin/StorageExplorer'


export const AppRouter = () => {
  const store = useStore() as AppStore
  useHashSync({ store, enabled: true })
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/visits" replace />} />
        <Route path="visits">
          <Route index element={<Home />} />
          <Route path=":visitId" element={<Home />} />
        </Route>
        <Route path="header/:visitId/:ccdName" element={<FItsHeaderPage />} />
        <Route path="config" element={<ConfigPage />} />
        <Route path="dev">
          <Route index element={<Dev />} />
        </Route>
        <Route path="admin">
          <Route path="storage" element={<StorageExplorer />} />
          <Route path="cache-entries" element={<CacheEntries />} />
        </Route>
      </Route>
    </Routes>
  )
}