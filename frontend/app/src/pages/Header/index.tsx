import { memo } from "react"
import { FlexiblePadding } from "../../components/layout"
import { LinkButton } from "../../components/LinkButton"
import { MaterialSymbol } from "../../components/MaterialSymbol"
import { useAdminPageEnabled } from "../../hooks/useAdminPageEnabled"
import styles from './styles.module.scss'


export const Header = memo(() => {
  const adminPageEnabled = useAdminPageEnabled()

  return (
    <div className={styles.header}>
      <FlexiblePadding />
      {adminPageEnabled && (
        <>
          <LinkButton to="/admin/status">System Status</LinkButton>
          <LinkButton to="/admin/jobs">Jobs</LinkButton>
          <LinkButton to="/admin/cache-entries">Cache Entries</LinkButton>
          <div style={{ width: '1em' }} />
        </>
      )}
      <LinkButton to="/query"><MaterialSymbol symbol="search" /></LinkButton>
      <LinkButton to="/config"><MaterialSymbol symbol="settings" /></LinkButton>
      <LinkButton to="/"><MaterialSymbol symbol="home" /></LinkButton>
    </div>
  )
})