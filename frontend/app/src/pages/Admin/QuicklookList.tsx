import { useListQuicklooksQuery } from "../../store/api/openapi"
import styles from './styles.module.scss'

export function QuicklookList() {
  const { data, isLoading, error } = useListQuicklooksQuery()

  if (isLoading) {
    return <div>Loading...</div>
  }

  if (error) {
    return <div>Error loading quicklooks</div>
  }

  return (
      <table className={styles.quicklookList}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Phase</th>
          </tr>
        </thead>
        <tbody>
          {data?.map(quicklook => (
            <tr key={quicklook.id}>
              <td>{quicklook.id}</td>
              <td>{quicklook.phase}</td>
            </tr>
          ))}
        </tbody>
      </table>
  )
}