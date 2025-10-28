import { useEffect, useRef } from 'react'
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
  const jobListRef = useRef<HTMLDivElement>(null)
  
  const showMonitor = !currentQuicklook.ready
  const metadata = currentQuicklook.metadata

  useEffect(() => {
    if (jobListRef.current && currentQuicklook.id && statusList) {
      const element = jobListRef.current.querySelector(`[data-visit="${currentQuicklook.id}"]`)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [currentQuicklook.id, statusList])

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
        <div className={styles.centerContent}>
          <LoadingSpinner />
        </div>
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
        <div ref={jobListRef} className={styles.fullWidth}>
          <JobList highlightKey={currentQuicklook.id} />
        </div>
      )}
    </div>
  )
}