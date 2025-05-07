import { Provider } from 'react-redux'
import { HashRouter } from 'react-router-dom'
import { AppRouter } from './router'
import { makeStore } from './store'


export function App() {
  const store = makeStore()
  return (
    <Provider store={store}>
      <HashRouter>
        <AppRouter />
      </HashRouter>
    </Provider>
  )
}