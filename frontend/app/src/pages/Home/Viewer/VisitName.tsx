import { formatVisitIdForDisplay } from '../../../quicklookId'
import { useHomeContext } from '../context'
import styles from './styles.module.scss'

export function VisitName() {
  const { currentQuicklook } = useHomeContext()
  if (!currentQuicklook.id) {
    return null
  }
  return (
    <div className={styles.visitName}>
      {formatVisitIdForDisplay(currentQuicklook.id)}
    </div>
  )
}