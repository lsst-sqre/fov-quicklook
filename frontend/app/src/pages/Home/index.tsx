import { memo } from "react"
import { wrapByHomeContext } from "./context"
import styles from './styles.module.scss'
import { Viewer } from "./Viewer"
import { ViewerSettings } from "./ViewerSettings"
import { Header } from "./Header"
import { VisitList } from "./VisitList"
import { LineProfiler } from "./LineProfiler"
import { Colorbar } from "./ViewerSettings/Colorbar"

export const Home = wrapByHomeContext(memo(() => {
  return (
    <div className={styles.home}>
      <Header />
      <div style={{ flexGrow: 1, display: 'flex' }}>
        <div style={{ width: 'min(30%, 400px)', display: 'flex', flexDirection: 'column' }}>
          <VisitList style={{ flexGrow: 1 }} />
          <ViewerSettings />
        </div>
        <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Viewer style={{ flexGrow: 1 }} />
          <Colorbar />
          <LineProfiler />
        </div>
      </div>
    </div>
  )
}))
