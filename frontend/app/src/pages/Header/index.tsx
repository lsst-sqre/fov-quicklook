import { memo, useCallback } from "react"
import { FlexiblePadding } from "../../components/layout"
import { LinkButton } from "../../components/LinkButton"
import { MaterialSymbol } from "../../components/MaterialSymbol"
import { useAdminPageEnabled } from "../../hooks/useAdminPageEnabled"
import { useDeleteAllCacheEntriesMutation } from "../../store/api/openapi"
import styles from './styles.module.scss'


export const Header = memo(() => {
  const adminPageEnabled = useAdminPageEnabled()

  return (
    <div className={styles.header}>
      <FlexiblePadding />
      {adminPageEnabled && (
        <>
          <DeleteAllCacheEntries />
          <div style={{ width: '1em' }} />
          <LinkButton to="/admin/status">System Status</LinkButton>
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



function DeleteAllCacheEntries() {
  const [deleteAll, { isLoading }] = useDeleteAllCacheEntriesMutation()
  return (
    <button disabled={isLoading} onClick={async () => await deleteAll()}>Clear Cache</button>
  )
}