import React from "react"
import ReactDOM from "react-dom/client"
import { App } from '../app'
import './styles.scss'

document.querySelector('.spinner')?.remove()

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App hashSync storageSync />
  </React.StrictMode>,
)
