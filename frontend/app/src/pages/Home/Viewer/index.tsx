import { Globe$, GlobeEventLayer$, GridLayer$, PanLayer$, RollLayer$, TouchLayer$, ZoomLayer$ } from '@stellar-globe/react-stellar-globe'
import { GlobeEventMap, GlobePointerEvent, V2 } from "@stellar-globe/stellar-globe"
import { memo, useCallback } from "react"
import { GenerateProgress } from '../../../appComponents/JobProgress'
import { Quicklook$ } from '../../../StellarGlobe/Quicklook/QuicklookLayer'
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { debounce } from '../../../utils/debounce'
import { useHomeContext } from "../context"
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

  const onPointerMove = useCallback((e: GlobePointerEvent) => {
    dispatch(homeSlice.actions.setMouseCursorClientCoord([e.clientCoord.x, e.clientCoord.y] as V2))
  }, [dispatch])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const debouncedCameraUpdate = useCallback(debounce(200, (e: GlobeEventMap['camera-move']) => {
    const { fovy, phi, roll, theta, za, zd, zp } = e.camera
    dispatch(homeSlice.actions.cameraParamsUpdated({ fovy, phi, roll, theta, za, zd, zp }))
  }), [dispatch])

  const onCameraMove: NonNullable<Parameters<typeof GlobeEventLayer$>[0]["onCameraMove"]> = useCallback(e => {
    dispatch(homeSlice.actions.cameraUpdated())
    debouncedCameraUpdate(e)
  }, [debouncedCameraUpdate, dispatch])

  const cameraParams = useAppSelector(state => state.home.cameraParams)

  const filterParams = useAppSelector(state => state.home.filterParams)
  const showFrame = useAppSelector(state => state.home.showFrame)

  return (
    <div style={{ ...style, position: 'relative', height: 0 }}>
      <Globe$
        ref={globeHandle}
        noDefaultLayers
        retina
        cameraParams={cameraParams}
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
        {showFrame && (<>
          <GridLayer$ />
          <CcdFrames />
        </>)
        }
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
