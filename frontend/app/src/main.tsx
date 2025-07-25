import '@stellar-globe/react-draggable-dialog/style.css'
import '@szhsin/react-menu/dist/index.css'
import '@szhsin/react-menu/dist/theme-dark.css'
import 'material-symbols/rounded.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './style.scss'
import { env } from './env'

window.addEventListener('load', () => {
  const pathname = window.location.pathname
  if (!pathname.startsWith(env.baseUrl)) {
    const redirectUrl = `${window.location.origin}${env.baseUrl}${pathname.startsWith('/') ? pathname : '/' + pathname}`
    window.location.href = redirectUrl
  }
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
