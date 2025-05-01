import { memo, useCallback } from "react"
import { FlexiblePadding } from "../../components/layout"
import { LinkButton } from "../../components/LinkButton"
import { MaterialSymbol } from "../../components/MaterialSymbol"
import { useAdminPageEnabled } from "../../hooks/useAdminPageEnabled"
import { useDeleteAllQuicklooksMutation } from "../../store/api/openapi"
import styles from './styles.module.scss'


type ExternalLinkButtonProps = {
  url: string
  windowName: string
  children: React.ReactNode
}

const ExternalLinkButton = ({ url, windowName, children }: ExternalLinkButtonProps) => {
  const handleClick = useCallback(() => {
    window.open(url, windowName)
  }, [url, windowName])

  return <button onClick={handleClick}>{children}</button>
}

export const Header = memo(() => {
  const [deleteAll,] = useDeleteAllQuicklooksMutation()

  const deleteAllAndRefresh = useCallback(async () => {
    if (!confirm('Are you sure you want to delete all quicklooks?')) {
      return
    }
    await deleteAll()
  }, [deleteAll])

  const queryIncludesAdminParam = window.location.search.includes('admin')
  const adminPageEnabled = useAdminPageEnabled() && queryIncludesAdminParam

  return (
    <div className={styles.header}>
      <FlexiblePadding />
      {adminPageEnabled && (
        <>
          <button onClick={deleteAllAndRefresh}>Clear Cache</button>
          <div style={{ width: '1em' }} />
          <ExternalLinkButton
            url="https://adc-gitlab.mtk.nao.ac.jp/gitlab/michitaro/rubin-quicklook-k8s/-/issues"
            windowName="fov-quicklook-issues"
          >
            Issues
          </ExternalLinkButton>
          <ExternalLinkButton
            url="https://usdf-rsp-dev.slac.stanford.edu/argo-cd/applications/argocd/fov-quicklook/fov-quicklook/fov-quicklook-frontend/logs?podName=&group=apps&kind=Deployment&name=fov-quicklook-frontend&viewPodNames=false&viewTimestamps=false&follow=true&showPreviousLogs=false"
            windowName="fov-quicklook-frontend-log"
          >
            FrontendLog
          </ExternalLinkButton>
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
