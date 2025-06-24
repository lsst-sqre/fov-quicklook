import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { QuicklookStatusProvider } from './pages/Home/context/quicklook'
import { AppRouter } from './router'
import { makeStore } from './store'
import { SystemInfo } from './store/api/openapi'
import { getSystemInfo } from './systemInfo'
import { env } from './env'
import { LoadingSpinner } from './components/Loading'
import { WindowCenter } from './components/layout'


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
  const store = makeStore(systemInfo)
  return (
    <Provider store={store}>
      <BrowserRouter basename={env.baseUrl}>
        <QuicklookStatusProvider>
          <AppRouter />
        </QuicklookStatusProvider>
      </BrowserRouter>
      <Toaster />
    </Provider>
  )
}
