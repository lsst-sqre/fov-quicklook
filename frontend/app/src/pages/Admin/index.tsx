import { PodsStatus } from "./PodsStatus"
import { QuicklookList } from "./QuicklookList"
import styles from './styles.module.scss'
import { useNavigate } from 'react-router-dom'

export function AdminPage() {
  const navigate = useNavigate()

  return (
    <div className={styles.adminPage}>
      <header className={styles.header}>
        <button onClick={() => navigate('/')}>
          Back to Home
        </button>
      </header>
      <details open>
        <summary>Quicklook List</summary>
        <QuicklookList />
      </details>
      <details>
        <summary>Pods Status</summary>
        <PodsStatus />
      </details>
    </div>
  )
}
