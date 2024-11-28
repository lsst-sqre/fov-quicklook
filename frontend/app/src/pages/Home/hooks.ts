import { SkyCoord, Tract, V2, angle } from "@stellar-globe/stellar-globe"
import { useCallback, useMemo } from "react"
import { useAppSelector } from "../../store/hooks"
import { includedInPolygon } from "../../utils/geometry"
import { useGlobe, useHomeContext } from "./context"

export function useResetView() {
  const { globeHandle } = useHomeContext()
  return useCallback((duration: number = 400) => {
    globeHandle.current?.().camera.jumpTo({ fovy: angle.deg2rad(3.6) }, { coord: SkyCoord.fromDeg(0, 0), duration })
  }, [globeHandle])
}

function useQuicklookMetadata() {
  const { currentQuicklook } = useHomeContext()
  return currentQuicklook.metadata
}

export function useWcs() {
  const metadata = useQuicklookMetadata()
  return useMemo(() => {
    if (metadata) {
      return Tract.fromFitsHeader(metadata.wcs)
    }
  }, [metadata])
}

function useMouseCursorSkyCoord(): SkyCoord | undefined {
  const _camera = useAppSelector(state => state.home.viewerCamera) // viewerCameraの変更のたびに再計算される必要がある
  const clientCoord = useAppSelector(state => state.home.mouseCursorClientCoord)
  const globe = useGlobe()
  return useMemo(() => {
    // eslint-disable-next-line @typescript-eslint/no-unused-expressions
    _camera
    if (globe) {
      return globe.canvas.coordFromClientCoord({ clientX: clientCoord[0], clientY: clientCoord[1] })
    }
  }, [_camera, clientCoord, globe])
}

export function useMouseCursorFocalPlaneCoord(): V2 {
  const wcs = useWcs()
  const skyCoord = useMouseCursorSkyCoord()
  return useMemo(() => {
    if (wcs && skyCoord) {
      return wcs.xyz2pixel(skyCoord.xyz)
    }
    return [0, 0]
  }, [skyCoord, wcs])
}

export function useFocusedCcd() {
  const metadata = useQuicklookMetadata()
  const [x, y] = useMouseCursorFocalPlaneCoord()

  return useMemo(() => {
    if (metadata && metadata.ccd_meta) {
      for (const ccd of metadata.ccd_meta) {
        const { ccd_id, bbox } = ccd
        const [p1, p2, p3, p4] = [
          [bbox.minx, bbox.miny],
          [bbox.maxx, bbox.miny],
          [bbox.maxx, bbox.maxy],
          [bbox.minx, bbox.maxy],
        ] as V2[]
        if (includedInPolygon([x, y], [p1, p2, p3, p4])) {
          return ccd
        }
      }
    }
  }, [metadata, x, y])
}

export function useFocusedAmp() {
  const focusedCcd = useFocusedCcd()
  const [x, y] = useMouseCursorFocalPlaneCoord()

  return useMemo(() => {
    if (focusedCcd?.amps) {
      for (const amp of focusedCcd.amps) {
        const b = amp.bbox
        if (includedInPolygon([x, y], [
          [b.minx, b.miny],
          [b.maxx, b.miny],
          [b.maxx, b.maxy],
          [b.minx, b.maxy]
        ])) {
          return amp
        }
      }
    }
  }, [focusedCcd, x, y])
}

// export function useFocusCcdFitsHeader() {
//   const shotId = useAppSelector(state => state.home.shotId)
//   const ccdMeta = useFocusCcd()
//   const { data, isFetching } = useShowFitsHeaderQuery({ shotId, ccdName: ccdMeta?.ccd_name ?? '' }, { skip: !ccdMeta })
//   return !isFetching ? data : undefined
// }
