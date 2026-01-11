import { useRef, useState } from 'react'
import { Toaster } from 'react-hot-toast'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { WindowCenter } from './components/layout'
import { LoadingSpinner } from './components/Loading'
import { env } from './env'
import { useCoordinatorIdMonitor } from './hooks/useCoordinatorIdMonitor'
import { QuicklookMetadataProvider } from './pages/Home/context/quicklook'
import { AppRouter } from './router'
import { makeStore } from './store'
import { SystemInfo } from './store/api/openapi'
import { getSystemInfo } from './systemInfo'


export function App() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  if (!systemInfo) {
    getSystemInfo().then(setSystemInfo).catch((error) => {
      console.error('Failed to fetch system info:', error)
    })
    return <WindowCenter><LoadingSpinner /></WindowCenter>
  }
  return (
    <RawApp systemInfo={systemInfo} />
  )
}


function RawApp({ systemInfo }: { systemInfo: SystemInfo }) {
  const storeRef = useRef<ReturnType<typeof makeStore>>()
  if (!storeRef.current) {
    storeRef.current = makeStore(systemInfo)
  }
  return (
    <Provider store={storeRef.current}>
      <CoordinatorIdMonitor />
      <BrowserRouter basename={env.baseUrl}>
        <QuicklookMetadataProvider>
          <AppRouter />
        </QuicklookMetadataProvider>
      </BrowserRouter>
      <Toaster />
    </Provider>
  )
}


function CoordinatorIdMonitor() {
  useCoordinatorIdMonitor()
  return null
}
