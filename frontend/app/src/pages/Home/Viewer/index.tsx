import { Globe$, GlobeEventLayer$, GridLayer$, PanLayer$, RollLayer$, TouchLayer$, ZoomLayer$ } from '@stellar-globe/react-stellar-globe'
import { angle, GlobePointerEvent, SkyCoord, V2 } from "@stellar-globe/stellar-globe"
import { memo, useCallback, useEffect } from "react"
import { Quicklook$ } from '../../../StellarGlobe/Quicklook/QuicklookLayer'
import { homeSlice } from "../../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { useHomeContext } from "../context"
import { CursorLine } from './CursorLine'
import { QuicklookProgress } from './QuicklookProgress'
import styles from './styles.module.scss'
import { CcdFrames } from './CcdFrames/CcdFrames'

type ViewerProps = {
  style?: React.CSSProperties
}

function useResetView() {
  const { globeHandle } = useHomeContext()
  return useCallback((duration: number = 400) => {
    globeHandle.current?.().camera.jumpTo({ fovy: angle.deg2rad(3.6) }, { coord: SkyCoord.fromDeg(0, 0), duration })
  }, [globeHandle])
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
  const id = useAppSelector(state => state.home.currentQuicklook)

  return (
    <div style={{ ...style, position: 'relative', height: 0 }}>
      <Globe$
        ref={globeHandle}
        noDefaultLayers
        retina
      >
        <GlobeEventLayer$ onPointerMove={onPointerMove} onCameraMove={onCameraMove} />
        {/* <MainContextMenu /> */}
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
        <CcdFrames />
      </Globe$>
      <CursorLine />
      {(currentQuicklook.status?.phase === 'processing' || currentQuicklook.metadata === undefined) && (
        <div className={styles.viewerBlock}>
          {currentQuicklook.status?.phase === 'processing' &&
            <QuicklookProgress status={currentQuicklook.status} />
          }
        </div>
      )}
      <div style={{ position: 'absolute', top: 0, left: 0, }}>
        {/* <pre>{JSON.stringify(currentQuicklook.status)}</pre> */}
        {/* <pre>{JSON.stringify(quicklookHandle)}</pre> */}
      </div>
    </div>
  )
})
