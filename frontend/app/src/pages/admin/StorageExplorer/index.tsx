import { createContext, useCallback, useContext, useMemo } from "react"
import { MaterialSymbol } from "../../../components/MaterialSymbol"
import { ListStorageEntriesApiResponse, useDeleteStorageEntriesByPrefixMutation, useDeleteStorageEntryMutation, useListStorageEntriesQuery } from "../../../store/api/openapi"
import styles from './styles.module.scss'
import { useSearchParams } from "react-router-dom"


type StorageContext = {
  path: string
  setPath: (path: string) => void
  refetch: () => void
}


const StorageContext = createContext<StorageContext | null>(null)


export function StorageExplorer() {
  const [searchParams, setSearchParams] = useSearchParams()
  const path = searchParams.get('path') || ''
  const { data: entries, refetch } = useListStorageEntriesQuery({ path })

  const setPath = useCallback((newPath: string) => {
    setSearchParams({ path: newPath })
  }, [setSearchParams])

  const context: StorageContext = useMemo(() => ({
    path,
    setPath,
    refetch,
  }), [path, setPath, refetch])

  const goUp = useCallback(() => {
    let _path = path.split("/").slice(0, -2).join("/") + "/"
    if (_path === '/') {
      _path = ''
    }
    setPath(_path)
  }, [path, setPath])

  return (
    <StorageContext.Provider value={context}>
      <div className={styles.storage}>
        <button onClick={goUp}><MaterialSymbol symbol="arrow_upward" /></button> &nbsp; {path}
        <hr />
        <table>
          <thead>
            <tr>
              <th>Path</th>
              <th>Size</th>
              <th>Type</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {entries?.map((entry) => (
              <Entry key={entry.name} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>
    </StorageContext.Provider>
  )
}


type EntryType = ListStorageEntriesApiResponse[number]


function Entry({
  entry,
}: {
  entry: EntryType,
}) {
  const { refetch, path, setPath } = useContext(StorageContext)!
  const goIn = useCallback(() => {
    setPath(`${path}${entry.name}`)
  }, [entry.name, path, setPath])
  const [deleteEntry] = useDeleteStorageEntryMutation()
  const [deleteEntryByPrefix] = useDeleteStorageEntriesByPrefixMutation()

  const handleDelete = useCallback(async () => {
    if (entry.type === 'directory') {
      await deleteEntryByPrefix({ prefix: `${path}${entry.name}` })
    } else {
      await deleteEntry({ path: `${path}${entry.name}` })
    }
    refetch()
  }, [deleteEntry, deleteEntryByPrefix, entry.name, entry.type, path, refetch])

  return (
    <tr>
      <td>{entry.name}</td>
      <td className={styles.size}>{entry.size}</td>
      <td className={styles.type}>
        {entry.type === 'directory' ?
          <MaterialSymbol symbol="folder" />
          :
          <MaterialSymbol symbol="draft" />
        }
      </td>
      <th>
        {entry.type === 'directory' && (
          <button onClick={goIn}>
            <MaterialSymbol symbol="arrow_forward" />
          </button>
        )}
        <button onClick={handleDelete}>
          <MaterialSymbol symbol="delete" />
        </button>
      </th>
    </tr>
  )
}
