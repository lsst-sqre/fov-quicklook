import '@stellar-globe/react-draggable-dialog/style.css'
import '@szhsin/react-menu/dist/index.css'
import '@szhsin/react-menu/dist/theme-dark.css'
import 'material-symbols/rounded.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { HashRouter } from 'react-router-dom'
import { AppRouter } from './router'
import { makeStore } from './store'
import './style.scss'


createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={makeStore()}>
      {/* <RouterProvider router={router} /> */}
      <HashRouter>
        <AppRouter/>
      </HashRouter>
    </Provider>
  </StrictMode>,
)
