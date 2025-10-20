import { JobList } from '../../../components/JobList'
import { GenerateSingleFitsTilesVisualizer } from '../../../components/JobStatusVisualizer/JobStatusVisualizer'
import { LoadingSpinner } from '../../../components/Loading'
import { useHomeContext } from '../context'
import styles from './styles.module.scss'

export function QuicklookJobMonitor() {
  const { currentQuicklook } = useHomeContext()
  const showMonitor = !currentQuicklook.ready

  if (showMonitor) {
    return (
      <div className={styles.viewerBlock}>
        {currentQuicklook.metadata?.type === 'progress' && Object.keys(currentQuicklook.metadata.progress).length > 0
          ?
          <GenerateSingleFitsTilesVisualizer tiles={currentQuicklook.metadata.progress} height="10vh" gap={true} />
          :
          <JobList highlightKey={currentQuicklook.id} />
        }
      </div>
    )
  }
}
