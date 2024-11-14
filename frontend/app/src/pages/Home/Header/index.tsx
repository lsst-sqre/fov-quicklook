import { memo, useCallback } from "react"
import { FlexiblePadding } from "../../../components/layout"
import { useDeleteAllQuicklooksMutation, useListQuicklooksQuery } from "../../../store/api/openapi"
import styles from './styles.module.scss'

export const Header = memo(() => {
  const { refetch } = useListQuicklooksQuery()
  const [deleteAll,] = useDeleteAllQuicklooksMutation()

  const deleteAllAndRefresh = useCallback(async () => {
    await deleteAll()
    await refetch()
  }, [deleteAll, refetch])

  return (
    <div className={styles.header}>
      <FlexiblePadding />
      <button onClick={deleteAllAndRefresh}>Clear Cache</button>
    </div>
  )
})
