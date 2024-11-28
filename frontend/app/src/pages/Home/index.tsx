import { memo } from "react"
import { wrapByHomeContext } from "./context"
import styles from './styles.module.scss'
import { Viewer } from "./Viewer"
import { ViewerSettings } from "./ViewerSettings"
import { Header } from "./Header"
import { VisitList } from "./VisitList"
import { LineProfiler } from "./LineProfiler"
import { Colorbar } from "./ViewerSettings/Colorbar"
import { useAppSelector } from "../../store/hooks"
import { Example } from "./HeaderViewerDialogs"


export const Home = wrapByHomeContext(memo(() => {
  const lineProfilerEnabled = useAppSelector(state => state.home.lineProfiler.enabled)

  return (
    <div className={styles.home}>
      <Header />
      <div style={{ flexGrow: 1, display: 'flex' }}>
        <div style={{ width: 'min(30%, 300px)', display: 'flex', flexDirection: 'column' }}>
          <VisitList style={{ flexGrow: 1 }} />
          <ViewerSettings />
          {/* <HeaderViewer /> */}
        </div>
        <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Viewer style={{ flexGrow: 1 }} />
          <Colorbar />
          {lineProfilerEnabled && <LineProfiler />}
        </div>
      </div>
      {/* <Example /> */}
    </div>
  )
}))
