import { JobList } from '../../../components/JobList'
import { GenerateSingleFitsTilesVisualizer } from '../../../components/JobStatusVisualizer/JobStatusVisualizer'
import { LoadingSpinner } from '../../../components/Loading'
import { useGetQuicklooksStatusQuery } from '../../../store/api/base'
import { useCreateQuicklookMutation } from '../../../store/api/openapi'
import { useHomeContext } from '../context'
import styles from './styles.module.scss'

export function QuicklookJobMonitor() {
  const { currentQuicklook } = useHomeContext()
  const { data: statusList } = useGetQuicklooksStatusQuery()
  const [createQuicklook] = useCreateQuicklookMutation()
  
  const showMonitor = !currentQuicklook.ready
  const metadata = currentQuicklook.metadata

  if (!showMonitor) {
    return null
  }

  const currentVisitStatus = currentQuicklook.id ? statusList?.[currentQuicklook.id] : undefined
  const isInList = currentVisitStatus !== undefined
  const isError = metadata?.type === 'error'

  const handleRetry = async () => {
    if (currentQuicklook.id) {
      await createQuicklook({ createQuicklookRequest: { visit: currentQuicklook.id } })
    }
  }

  return (
    <div className={styles.viewerBlock}>
      {!isInList && !isError ? (
        <LoadingSpinner />
      ) : isError ? (
        <div className={styles.errorContainer}>
          <div className={styles.errorMessage}>
            Error loading quicklook
          </div>
          <button className={styles.retryButton} onClick={handleRetry}>
            Retry Request
          </button>
        </div>
      ) : metadata?.type === 'progress' && Object.keys(metadata.progress).length > 0 ? (
        <GenerateSingleFitsTilesVisualizer tiles={metadata.progress} height="10vh" gap={true} />
      ) : (
        <JobList highlightKey={currentQuicklook.id} />
      )}
    </div>
  )
}
