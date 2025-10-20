import { useEffect } from 'react'
import { CacheEntry, useDeleteCacheEntryMutation, useListCacheEntriesQuery } from "../../../store/api/openapi"
import styles from './styles.module.scss'


export function CacheEntries() {
  const { data: entries, refetch, isLoading } = useListCacheEntriesQuery(undefined, { refetchOnMountOrArgChange: true })

  useEffect(() => {
    const intervalId = setInterval(() => {
      refetch()
    }, 60_000)
    return () => clearInterval(intervalId)
  }, [refetch])

  return (
    <div className={styles.cacheEntries}>
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
      <td>{entry.visit_name}</td>
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