import { Globe$, GlobeEventLayer$, GridLayer$, PanLayer$, RollLayer$, TouchLayer$, ZoomLayer$ } from '@stellar-globe/react-stellar-globe'
import { GlobeEventMap, GlobePointerEvent, V2 } from "@stellar-globe/stellar-globe"
import { memo, useCallback, type ComponentType, type ForwardRefExoticComponent } from "react"
import { Quicklook$ } from '../../../StellarGlobe/Quicklook/QuicklookLayer'
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { debounce } from '../../../utils/debounce'
import { useHomeContext } from "../context"
import { CcdFrames, HighlitedCcds } from './CcdFrames/CcdFrames'
import { CursorLine } from './CursorLine'
import { Info } from './Info'
import { ViewerContextMenu } from './ViewerContextMenu'
import { QuicklookJobMonitor } from './QuicklookJobMonitor'
import { CompactStatus } from './CompactStatus'
import { VisitName } from './VisitName'

type ViewerProps = {
  style?: React.CSSProperties
}

// ponytail: local file deps can bring their own React types; cast at the JSX boundary.
const GlobeCompat = Globe$ as unknown as ForwardRefExoticComponent<any>
const GlobeEventLayerCompat = GlobeEventLayer$ as unknown as ComponentType<any>
const GridLayerCompat = GridLayer$ as unknown as ComponentType<any>
const PanLayerCompat = PanLayer$ as unknown as ComponentType<any>
const RollLayerCompat = RollLayer$ as unknown as ComponentType<any>
const TouchLayerCompat = TouchLayer$ as unknown as ComponentType<any>
const ZoomLayerCompat = ZoomLayer$ as unknown as ComponentType<any>

export const Viewer = memo(({ style }: ViewerProps) => {
  const { globeHandle, quicklookLayerHandle: quicklookHandle, currentQuicklook } = useHomeContext()
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
      <GlobeCompat
        ref={globeHandle}
        noDefaultLayers
        retina
        cameraParams={cameraParams}
      >
        <GlobeEventLayerCompat onPointerMove={onPointerMove} onCameraMove={onCameraMove} />
        <ViewerContextMenu />
        <ZoomLayerCompat />
        <RollLayerCompat />
        <TouchLayerCompat />
        <PanLayerCompat />
        {currentQuicklook.metadata?.type === 'ready' &&
          <Quicklook$
            ref={quicklookHandle}
            metadata={currentQuicklook.metadata}
            filterParams={filterParams}
          />
        }
        {showFrame && (<>
          <GridLayerCompat />
          <CcdFrames />
        </>)
        }
        <HighlitedCcds />
      </GlobeCompat>
      <CursorLine />
      <VisitName />
      <Info />
      <QuicklookJobMonitor />
      <CompactStatus />
    </div>
  )
})
