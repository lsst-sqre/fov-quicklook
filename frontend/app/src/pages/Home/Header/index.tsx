import { memo, useCallback } from "react"
import { FlexiblePadding } from "../../../components/layout"
import { useDeleteAllQuicklooksMutation, useListQuicklooksQuery } from "../../../store/api/openapi"
import styles from './styles.module.scss'
import { MainMenu } from "./MainMenu"
import { LinkButton } from "../../../components/LinkButton"

export const Header = memo(() => {
  const { refetch } = useListQuicklooksQuery()
  const [deleteAll,] = useDeleteAllQuicklooksMutation()

  const deleteAllAndRefresh = useCallback(async () => {
    await deleteAll()
    await refetch()
  }, [deleteAll, refetch])

  const openIssues = useCallback(() => {
    window.open(
      'https://adc-gitlab.mtk.nao.ac.jp/gitlab/michitaro/rubin-quicklook-k8s/-/issues',
      'fov-quicklook-issues',
    )
  }, [])

  return (
    <div className={styles.header}>
      <MainMenu />
      <FlexiblePadding />
      <LinkButton to="/admin">Admin</LinkButton>
      <button onClick={openIssues}>Issues</button>
      <button onClick={deleteAllAndRefresh}>Clear Cache</button>
    </div>
  )
})
