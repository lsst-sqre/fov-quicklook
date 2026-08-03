import { memo, useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useSearchParams } from "react-router-dom"
import { useGetVisitResolutionQuery } from "../../store/api/openapi"
import { ButlerScopeId, hasExplicitDetectorSelection, homeSlice, parseDetectorName, writeHighlightedCcds } from "../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { extractScopeIdFromVisitId, parseVisitId } from "../../quicklookId"
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
import { extractSearchDateFromVisitId } from "./visitSearch"
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
  useApplyResolvedVisitState()
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
      dispatch(homeSlice.actions.setSearchString(extractSearchDateFromVisitId(visitId)))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (visitId) {
      const dataSource = extractScopeIdFromVisitId(visitId)
      if (dataSource) {
        dispatch(homeSlice.actions.setDataSource(dataSource))
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}


function extractDataTypeFromVisitId(visitId: string): ButlerScopeId | undefined {
  return extractScopeIdFromVisitId(visitId) as ButlerScopeId | undefined
}


function isByUuidVisitId(visitId: string | undefined) {
  if (!visitId) {
    return false
  }
  try {
    return parseVisitId(visitId).isByUuid
  } catch {
    return false
  }
}


function useApplyResolvedVisitState() {
  const dispatch = useAppDispatch()
  const { visitId } = useParams()
  const [searchParams] = useSearchParams()
  const dataSource = useAppSelector(state => state.home.dataSource)
  const highlightedCcds = useAppSelector(state => state.home.hilightedCcdId)
  const hasExplicitDetector = hasExplicitDetectorSelection(searchParams)
  const isByUuidVisit = isByUuidVisitId(visitId)
  const { data: resolution } = useGetVisitResolutionQuery(
    { visitName: visitId! },
    { skip: !visitId || !isByUuidVisit },
  )

  useEffect(() => {
    if (!resolution) return

    const resolvedDataSource = extractDataTypeFromVisitId(resolution.visit_name)
    if (resolvedDataSource && dataSource !== resolvedDataSource) {
      dispatch(homeSlice.actions.setDataSource(resolvedDataSource))
    }

    if (
      !hasExplicitDetector &&
      highlightedCcds.length === 0 &&
      resolution.detector !== null &&
      resolution.detector !== undefined
    ) {
      dispatch(homeSlice.actions.setHighlightCcds([parseDetectorName(`${resolution.detector}`)]))
    }
  }, [dataSource, dispatch, hasExplicitDetector, highlightedCcds.length, resolution])
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
    const next = writeHighlightedCcds(searchParams, ccds)
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true })
    }
  }, [ccds, searchParams, setSearchParams])
}
