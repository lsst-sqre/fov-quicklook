import { memo, useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { homeSlice } from "../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { wrapByHomeContext } from "./context"
import { LineProfiler } from "./LineProfiler"
import { MainMenu } from "./MainMenu"
import styles from './styles.module.scss'
import { Viewer } from "./Viewer"
import { ViewerSettings } from "./ViewerSettings"
import { Colorbar } from "./ViewerSettings/Colorbar"
import { VisitList } from "./VisitList"
import { DataTypeSwitch } from "./DataTypeSwitch"

export const Home = wrapByHomeContext(memo(() => {
  const lineProfilerEnabled = useAppSelector(state => state.home.lineProfiler.enabled)
  useSyncQuicklookWithUrl()

  return (
    <div className={styles.home}>
      <div style={{ flexGrow: 1, display: 'flex' }}>
        <div style={{ width: 'min(30%, 300px)', display: 'flex', flexDirection: 'column' }}>
          <VisitList style={{ flexGrow: 1 }} />
          <ViewerSettings />
        </div>
        <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Viewer style={{ flexGrow: 1 }} />
          <Colorbar />
          {lineProfilerEnabled && <LineProfiler />}
          <div className={styles.buttons}>
            <DataTypeSwitch />
            <MainMenu />
          </div>
        </div>
      </div>
    </div>
  )
}))


const useSyncQuicklookWithUrl = () => {
  const { visitId } = useParams()
  const dispatch = useAppDispatch()
  const currentQuicklook = useAppSelector(state => state.home.currentQuicklook)
  const navigate = useNavigate()

  useEffect(() => {
    if (visitId) {
      dispatch(homeSlice.actions.setCurrentQuicklook(visitId))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (currentQuicklook) {
      navigate(`/visits/${currentQuicklook}`, { replace: true })
    }
  }, [currentQuicklook, navigate])
}
