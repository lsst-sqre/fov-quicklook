import '@szhsin/react-menu/dist/index.css'
import '@szhsin/react-menu/dist/theme-dark.css'
import 'material-symbols/rounded.css'
import '@stellar-globe/react-draggable-dialog/style.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { createHashRouter, RouterProvider } from 'react-router-dom'
import './style.scss'
import { Home } from './pages/Home'
import { makeStore } from './store'


const router = createHashRouter([
  {
    path: "/",
    element: (
      <Home />
    ),
  },
])


createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={makeStore()}>
      <RouterProvider router={router} />
    </Provider>
  </StrictMode>,
)
