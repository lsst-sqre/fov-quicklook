import { memo, useCallback } from "react"
import { FlexiblePadding } from "../../../components/layout"
import { useDeleteAllQuicklooksMutation, useListQuicklooksQuery } from "../../../store/api/openapi"
import styles from './styles.module.scss'
import { MainMenu } from "./MainMenu"

export const Header = memo(() => {
  const { refetch } = useListQuicklooksQuery()
  const [deleteAll,] = useDeleteAllQuicklooksMutation()

  const deleteAllAndRefresh = useCallback(async () => {
    await deleteAll()
    await refetch()
  }, [deleteAll, refetch])

  return (
    <div className={styles.header}>
      <MainMenu />
      <FlexiblePadding />
      <button onClick={deleteAllAndRefresh}>Clear Cache</button>
    </div>
  )
})
