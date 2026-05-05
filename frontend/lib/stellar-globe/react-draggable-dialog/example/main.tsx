import React from 'react'
import ReactDOM from 'react-dom/client'
import { Example } from './Example'
import './style.scss'


function main() {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <Example />
    </React.StrictMode>,
  )
}

main()
