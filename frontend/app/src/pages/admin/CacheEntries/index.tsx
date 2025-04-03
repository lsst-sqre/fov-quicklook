import { useCleanupCacheEntriesMutation, useListCacheEntriesQuery } from "../../../store/api/openapi"
import { useEffect } from 'react'
import styles from './styles.module.scss'

export function CacheEntries() {
  const { data: entries, refetch } = useListCacheEntriesQuery()
  const [cleanup] = useCleanupCacheEntriesMutation()

  useEffect(() => {
    const intervalId = setInterval(() => {
      refetch()
    }, 60_000)
    return () => clearInterval(intervalId)
  }, [refetch])

  const handleCleanup = async () => {
    await cleanup()
    refetch()
  }

  return (
    <div className={styles.cacheEntries}>
      <button onClick={refetch}>Refresh</button>
      <button onClick={handleCleanup}>Cleanup</button>
      <table>
        <thead>
          <tr>
            <th>id</th>
            <th>phase</th>
            <th>updated_at</th>
            <th>minutes ago</th>
          </tr>
        </thead>
        <tbody>
          {entries?.map(entry => (
            <tr key={entry.id}>
              <td>{entry.id}</td>
              <td>{entry.phase}</td>
              <td>{entry.updated_at}</td>
              <td>{calculateMinutesAgo(entry.updated_at).toFixed(0)} min</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


function parseUtcDate(dateString: string) {
  // Convert the date string (in UTC) to a Date object
  // dateString is in the format "2025-04-03T20:27:21.237940"
  return new Date(dateString + 'Z')
}

function calculateMinutesAgo(dateString: string): number {
  const date = parseUtcDate(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = diffMs / (1000 * 60)
  return diffMinutes
}
