import { Globe$, GlobeEventLayer$, GridLayer$, PanLayer$, RollLayer$, TouchLayer$, ZoomLayer$ } from '@stellar-globe/react-stellar-globe'
import { GlobePointerEvent, V2 } from "@stellar-globe/stellar-globe"
import { memo, useCallback, useEffect } from "react"
import { GenerateProgress } from '../../../appComponents/JobProgress'
import { Quicklook$ } from '../../../StellarGlobe/Quicklook/QuicklookLayer'
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { useHomeContext, useResetView } from "../context"
import { CcdFrames } from './CcdFrames/CcdFrames'
import { CursorLine } from './CursorLine'
import { Info } from './Info'
import styles from './styles.module.scss'
import { ViewerContextMenu } from './ViewerContextMenu'

type ViewerProps = {
  style?: React.CSSProperties
}

export const Viewer = memo(({ style }: ViewerProps) => {
  const { globeHandle, quicklookHandle, currentQuicklook } = useHomeContext()
  const dispatch = useAppDispatch()
  const resetView = useResetView()

  useEffect(() => {
    resetView(0)
  }, [resetView])

  const onPointerMove = useCallback((e: GlobePointerEvent) => {
    dispatch(homeSlice.actions.setMouseCursorClientCoord([e.clientCoord.x, e.clientCoord.y] as V2))
  }, [dispatch])

  const onCameraMove: NonNullable<Parameters<typeof GlobeEventLayer$>[0]["onCameraMove"]> = useCallback(_e => {
    dispatch(homeSlice.actions.setViewerCamera({}))
  }, [dispatch])

  const filterParams = useAppSelector(state => state.home.filterParams)
  const showFrame = useAppSelector(state => state.home.showFrame)

  return (
    <div style={{ ...style, position: 'relative', height: 0 }}>
      <Globe$
        ref={globeHandle}
        noDefaultLayers
        retina
      >
        <GlobeEventLayer$ onPointerMove={onPointerMove} onCameraMove={onCameraMove} />
        <ViewerContextMenu />
        <ZoomLayer$ />
        <RollLayer$ />
        <TouchLayer$ />
        <PanLayer$ />
        {currentQuicklook.metadata &&
          <Quicklook$
            ref={quicklookHandle}
            metadata={currentQuicklook.metadata}
            filterParams={filterParams}
          />
        }
        <GridLayer$ />
        {showFrame && <CcdFrames />}
      </Globe$>
      <CursorLine />
      <Info />
      {!!currentQuicklook.metadata || (
        <div className={styles.viewerBlock}>
          <GenerateProgress s={currentQuicklook.status} />
        </div>
      )}
    </div>
  )
})
