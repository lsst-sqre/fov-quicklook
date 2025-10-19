import { JobStatusVisualizer } from '../../../components/JobStatusVisualizer/JobStatusVisualizer'
import { useGetQuicklooksStatusQuery } from '../../../store/api/base'
import { useGetAllQuicklookJobsQuery } from '../../../store/api/openapi'
import styles from './styles.module.scss'

export function Jobs() {
  const { data: statusList } = useGetQuicklooksStatusQuery()

  return (
    <div className={styles.container}>
      {statusList && Object.entries(statusList).map(([key, status]) => (
        <JobStatusVisualizer key={key} status={status} />
      ))}
    </div>
  )
}
