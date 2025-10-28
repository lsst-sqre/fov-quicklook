import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { CacheEntry, useDeleteCacheEntryMutation, useGetSystemInfoQuery, useListCacheEntriesQuery } from "../../../store/api/openapi"
import { Progress } from '../../../components/Progress'
import styles from './styles.module.scss'


export function CacheEntries() {
  const { data: entries, refetch, isLoading } = useListCacheEntriesQuery(undefined, { refetchOnMountOrArgChange: true })
  const { data: systemInfo } = useGetSystemInfoQuery()

  useEffect(() => {
    const intervalId = setInterval(() => {
      refetch()
    }, 60_000)
    return () => clearInterval(intervalId)
  }, [refetch])

  const totalUsage = entries?.reduce((sum, entry) => sum + entry.disk_usage, 0) ?? 0
  const maxUsage = systemInfo?.max_object_storage_usage ?? 0
  const usagePercent = maxUsage > 0 ? (totalUsage / maxUsage * 100).toFixed(1) : '0'

  return (
    <div className={styles.cacheEntries}>
      <div className={styles.summary}>
        <div className={styles.summaryText}>
          <p>Total Usage: {humanReadableSize(totalUsage)} / {humanReadableSize(maxUsage)} ({usagePercent}%)</p>
        </div>
        <div className={styles.progressContainer}>
          <Progress count={totalUsage} total={maxUsage} width="100%" rounded={true} />
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Visit</th>
            <th>Ready</th>
            <th>Size</th>
            <th>Created At</th>
            <th>Delete</th>
          </tr>
        </thead>
        <tbody>
          {isLoading && (
            <tr>
              <td colSpan={5}>Loading...</td>
            </tr>
          )}
          {entries?.slice().sort((a, b) => -a.created_at.localeCompare(b.created_at)).map(entry => (
            <CacheEntryRow key={entry.visit_name} entry={entry} onDelete={refetch} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface CacheEntryRowProps {
  entry: CacheEntry
  onDelete: () => void
}

function CacheEntryRow({ entry, onDelete }: CacheEntryRowProps) {
  const [deleteEntry, { isLoading: isDeleting }] = useDeleteCacheEntryMutation()

  const handleDelete = async () => {
    await deleteEntry({ visitName: entry.visit_name })
    onDelete()
  }

  return (
    <tr>
      <td>
        <Link to={`/visits/${encodeURIComponent(entry.visit_name)}`}>
          {entry.visit_name}
        </Link>
      </td>
      <td>{entry.ready ? 'Yes' : 'No'}</td>
      <td>{humanReadableSize(entry.disk_usage)}</td>
      <td>{entry.created_at}</td>
      <td>
        <button
          disabled={isDeleting}
          onClick={handleDelete}
        >
          Delete
        </button>
      </td>
    </tr>
  )
}

function humanReadableSize(size: number): string {
  if (size === 0) {
    return `0 B`
  }
  const i = Math.floor(Math.log(size) / Math.log(1024))
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  return `${(size / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`
}