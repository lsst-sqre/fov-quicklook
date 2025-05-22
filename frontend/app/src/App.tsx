import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { AppRouter } from './router'
import { makeStore } from './store'
import { env } from './env'
import { QuicklookStatusProvider } from './pages/Home/context/quicklook'


export function App() {
  const store = makeStore()
  return (
    <Provider store={store}>
      <BrowserRouter basename={env.baseUrl}>
        <QuicklookStatusProvider>
          <AppRouter />
        </QuicklookStatusProvider>
      </BrowserRouter>
    </Provider>
  )
}
