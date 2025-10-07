import { Outlet } from 'react-router-dom'
import { Header } from '../Header'
import styles from './styles.module.scss'

export function Layout() {
  return (
    <div className={styles.layout}>
      <Header />
      <div className={styles.outlet}>
        <Outlet />
      </div>
    </div>
  )
}
