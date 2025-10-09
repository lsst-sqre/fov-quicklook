import { useGetQuicklooksStatusQuery } from "../../store/api/base"
import { useCreateQuicklookMutation, useGetAllQuicklookJobsQuery } from "../../store/api/openapi"
import styles from './styles.module.scss'
import { JobStatusVisualizer } from '../../components/JobStatusVisualizer/JobStatusVisualizer'

export function Dev() {
  const jobs = useGetAllQuicklookJobsQuery()
  // const [createQuicklook] = useCreateQuicklookMutation()

  // const handleCreateQuicklook = async () => {
  //   await createQuicklook({ createQuicklookRequest: { visit: 'raw:broccoli' } })
  // }

  const { data: statusList } = useGetQuicklooksStatusQuery()

  return (
    <div className={styles.container}>
      <h1>Dev</h1>
      {/* <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
        <button onClick={handleCreateQuicklook}>Create Quicklook</button>
      </div> */}
      {statusList && Object.entries(statusList).map(([key, status]) => (
        <JobStatusVisualizer key={key} status={status} />
      ))}
    </div>
  )
}
