import { memo, useCallback } from "react"
import { FlexiblePadding } from "../../components/layout"
import { LinkButton } from "../../components/LinkButton"
import { MaterialSymbol } from "../../components/MaterialSymbol"
import { useAdminPageEnabled } from "../../hooks/useAdminPageEnabled"
import { useDeleteAllQuicklooksMutation, useListQuicklooksQuery } from "../../store/api/openapi"
import styles from './styles.module.scss'


export const Header = memo(() => {
  const { refetch } = useListQuicklooksQuery()
  const [deleteAll,] = useDeleteAllQuicklooksMutation()

  const deleteAllAndRefresh = useCallback(async () => {
    if (!confirm('Are you sure you want to delete all quicklooks?')) {
      return
    }
    await deleteAll()
    await refetch()
  }, [deleteAll, refetch])

  const openIssues = useCallback(() => {
    window.open(
      'https://adc-gitlab.mtk.nao.ac.jp/gitlab/michitaro/rubin-quicklook-k8s/-/issues',
      'fov-quicklook-issues',
    )
  }, [])

  const queryIncludesAdminParam = window.location.search.includes('admin')
  const adminPageEnabled = useAdminPageEnabled() && queryIncludesAdminParam

  return (
    <div className={styles.header}>
      <FlexiblePadding />
      {adminPageEnabled && (
        <>
          <button onClick={openIssues}>Issues</button>
          <button onClick={deleteAllAndRefresh}>Clear Cache</button>
          <div style={{ width: '1em' }} />
          <LinkButton to="/admin/pod_status">PodStatus</LinkButton>
          <LinkButton to="/admin/jobs">Jobs</LinkButton>
          <LinkButton to="/admin/cache-entries">Cache Entries</LinkButton>
          <LinkButton to="/admin/storage">Storage</LinkButton>
          <div style={{ width: '1em' }} />
        </>
      )}
      <LinkButton to="/config"><MaterialSymbol symbol="settings" /></LinkButton>
      <LinkButton to="/"><MaterialSymbol symbol="home" /></LinkButton>
    </div>
  )
})
