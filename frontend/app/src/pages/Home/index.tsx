import { memo, useEffect, useRef } from "react"
import { useParams, useSearchParams } from "react-router-dom"
import { CcdDataType, homeSlice } from "../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { wrapByHomeContext } from "./context"
import { DataTypeSwitch } from "./DataTypeSwitch"
import { LineProfiler } from "./LineProfiler"
import { MainMenu } from "./MainMenu"
import styles from './styles.module.scss'
import { Viewer } from "./Viewer"
import { ViewerSettings } from "./ViewerSettings"
import { Colorbar } from "./ViewerSettings/Colorbar"
import { VisitList } from "./VisitList"
import { useOnChange } from "../../hooks/useOnChange"

export const Home = wrapByHomeContext(memo(() => {
  const lineProfilerEnabled = useAppSelector(state => state.home.lineProfiler.enabled)
  useSetInitialSearchConditions()
  useSyncHighlightCcdsWithUrl()

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


const useSetInitialSearchConditions = () => {
  const searchString = useAppSelector(state => state.home.searchString)
  const { visitId } = useParams()
  const dispatch = useAppDispatch()

  useEffect(() => {
    if (searchString === '' && visitId) {
      dispatch(homeSlice.actions.setSearchString(extractDateFromVisitId(visitId)))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (visitId) {
      const dataSource = extractDataSourceFromVisitId(visitId)
      if (dataSource) {
        dispatch(homeSlice.actions.setDataSource(dataSource))
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}


function extractDateFromVisitId(visitId: string) {
  /*
   * post_isr_image:2025051900437 のようなテキストから20250519を抽出する
   * 形式がマッチしなければ '' を返す
   */
  if (!visitId.match(/^.+:\d{13}$/)) {
    return ''
  }
  const date = visitId.split(':')[1]
  return date.slice(0, 8)
}


function extractDataSourceFromVisitId(visitId: string): CcdDataType | undefined {
  /*
   * post_isr_image:2025051900437 のようなテキストから post_isr_image を抽出する
   * 形式がマッチしなければ undefined を返す
   */
  if (!visitId.match(/^(.+):\d{13}$/)) {
    return undefined
  }
  const dataSource = visitId.split(':')[0]
  return dataSource as CcdDataType
}


function useSyncHighlightCcdsWithUrl() {
  const dispatch = useAppDispatch()
  const [searchParams, setSearchParams] = useSearchParams()
  const { visitId } = useParams()
  const ccds = useAppSelector(state => state.home.hilightedCcdId)

  useOnChange(visitId, () => {
    dispatch(homeSlice.actions.clearHighlightCcd())
  })

  useEffect(() => {
    const serialized = ccds.join(',')
    searchParams.set('detectors', serialized)
    setSearchParams(searchParams, { replace: true })
  }, [ccds, searchParams, setSearchParams])
}
