import { memo } from "react"
import { useAppSelector } from "../../store/hooks"
import { wrapByHomeContext } from "./context"
import { Header } from "./Header"
import { LineProfiler } from "./LineProfiler"
import styles from './styles.module.scss'
import { Viewer } from "./Viewer"
import { ViewerSettings } from "./ViewerSettings"
import { Colorbar } from "./ViewerSettings/Colorbar"
import { VisitList } from "./VisitList"


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
