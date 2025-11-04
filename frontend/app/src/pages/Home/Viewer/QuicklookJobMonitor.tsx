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

  const statusListCount = statusList ? Object.keys(statusList).length : 0

  useEffect(() => {
    if (jobListRef.current && currentQuicklook.id && statusList) {
      const element = jobListRef.current.querySelector(`[data-visit="${currentQuicklook.id}"]`)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
    }
  }, [currentQuicklook.id, statusListCount])

  if (!showMonitor) {
    return null
  }

  const handleRetry = async () => {
    if (currentQuicklook.id) {
      await createQuicklook({ createQuicklookRequest: { visit: currentQuicklook.id } })
    }
  }

  // Error state
  if (metadata?.type === 'error') {
    return (
      <div className={styles.viewerBlock}>
        <div className={styles.centerContent}>
          <div className={styles.errorContainer}>
            <div className={styles.errorMessage}>
              Error loading quicklook
            </div>
            {/* <button className={styles.retryButton} onClick={handleRetry}>
              Retry Request
            </button> */}
          </div>
        </div>
      </div>
    )
  }

  // Progress state
  if (metadata?.type === 'progress') {
    return (
      <div className={styles.viewerBlock}>
        <div className={styles.centerContent}>
          <div className={styles.visualizerWrapper}>
            {Object.keys(metadata.progress).length === 0 && (
              <div className={styles.visualizerOverlay}>
                <LoadingSpinner />
              </div>
            )}
            <GenerateSingleFitsTilesVisualizer tiles={metadata.progress} height="10vh" gap={true} />
          </div>
        </div>
      </div>
    )
  }

  // Pending state
  if (metadata?.type === 'pending') {
    return (
      <div className={styles.viewerBlock}>
        <div ref={jobListRef} className={styles.fullWidth}>
          <JobList highlightKey={currentQuicklook.id} />
        </div>
      </div>
    )
  }

  // Ready state (shouldn't happen since showMonitor is false for ready)
  return (
    <div className={styles.viewerBlock}>
      <div className={styles.centerContent}>
        <LoadingSpinner />
      </div>
    </div>
  )
}