import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import '../node_modules/@stellar-globe/app/dist/style.css'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
