import { memo, useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useSearchParams } from "react-router-dom"
import { CcdDataType, homeSlice } from "../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { ShortcutHelpDialog } from "./ShortcutHelpDialog"
import { wrapByHomeContext } from "./context"
import { HomeShortcutHandlers, useHomeKeyboardShortcuts } from "./keyboardShortcuts"
import { DataTypeSwitch } from "./DataTypeSwitch"
import { LineProfiler } from "./LineProfiler"
import { MainMenu } from "./MainMenu"
import styles from './styles.module.scss'
import { useHomeActions } from "./useHomeActions"
import { Viewer } from "./Viewer"
import { ViewerSettings } from "./ViewerSettings"
import { Colorbar } from "./ViewerSettings/Colorbar"
import { VisitList } from "./VisitList"
import { useOnChange } from "../../hooks/useOnChange"

export const Home = wrapByHomeContext(memo(() => {
  const { lineProfilerEnabled, recenter, rotateClockwise, rotateCounterClockwise, toggleLineProfiler } = useHomeActions()
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false)
  const toggleShortcutHelp = useCallback(() => {
    setShortcutHelpOpen(current => !current)
  }, [])
  const closeShortcutHelp = useCallback(() => {
    setShortcutHelpOpen(false)
  }, [])
  const shortcutHandlers = useMemo<HomeShortcutHandlers>(() => ({
    recenter,
    rotateClockwise,
    rotateCounterClockwise,
    toggleLineProfiler,
    toggleShortcutHelp,
  }), [recenter, rotateClockwise, rotateCounterClockwise, toggleLineProfiler, toggleShortcutHelp])

  useHomeKeyboardShortcuts(shortcutHandlers)
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
      <ShortcutHelpDialog onClose={closeShortcutHelp} open={shortcutHelpOpen} />
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
      const dataSource = extractDataTypeFromVisitId(visitId)
      if (dataSource) {
        dispatch(homeSlice.actions.setDataSource(dataSource))
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}


function extractDateFromVisitId(visitId: string) {
  /*
   * embargo:raw:2025051900437 のようなテキストから20250519を抽出する
   * 形式がマッチしなければ '' を返す
   */
  const parts = visitId.split(':')
  const last = parts[parts.length - 1]
  if (!last?.match(/^\d{13}$/)) {
    return ''
  }
  return last.slice(0, 8)
}


function extractDataTypeFromVisitId(visitId: string): CcdDataType | undefined {
  /*
   * embargo:raw:2025051900437 のようなテキストから embargo:raw を抽出する
   * 形式がマッチしなければ undefined を返す
   */
  const parts = visitId.split(':')
  if (parts.length < 3) {
    return undefined
  }
  return parts.slice(0, -1).join(':') as CcdDataType
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
