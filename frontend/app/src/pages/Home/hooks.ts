import { SkyCoord, Tract, V2, angle } from "@stellar-globe/stellar-globe"
import { useCallback, useMemo } from "react"
import { useGlobe, useHomeContext } from "./context"
import { useAppSelector } from "../../store/hooks"

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

export function useCrvalOriginWcs() {
  const shotmeta = useQuicklookMetadata()
  return useMemo(() => {
    if (shotmeta) {
      const wcs = { ...shotmeta.wcs }
      Object.assign(wcs, { CRPIX1: 0, CRPIX2: 0 })
      return Tract.fromFitsHeader(wcs)
    }
  }, [shotmeta])
}

export function useWcs() {
  const shotmeta = useQuicklookMetadata()
  return useMemo(() => {
    if (shotmeta) {
      return Tract.fromFitsHeader(shotmeta.wcs)
    }
  }, [shotmeta])
}

export function useMouseCursorSkyCoord(): SkyCoord | undefined {
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

export function useMouseCursorCrvalOriginFocalPlaneCoord(): V2 {
  const wcs = useCrvalOriginWcs()
  const skyCoord = useMouseCursorSkyCoord()
  return useMemo(() => {
    if (wcs && skyCoord) {
      return wcs.xyz2pixel(skyCoord.xyz)
    }
    return [0, 0]
  }, [skyCoord, wcs])
}

// export function useFocusCcd() {
//   const metadata = useQuicklookMetadata()
//   const [x, y] = useMouseCursorFocalPlaneCoord()

//   return useMemo(() => {
//     if (metadata) {
//       for (const ccdname in metadata.ccd_meta) {
//         const ccdmeta = metadata.ccd_meta[ccdname]
//         const [p1, p2, p3, p4] = ccdmeta.ccd_corners
//         if (includedInPolygon([x, y], [p1, p2, p3, p4])) {
//           return ccdmeta
//         }
//       }
//     }
//   }, [metadata, x, y])
// }

// export function useFocusAmp() {
//   const metadata = useQuicklookMetadata()
//   const focusCcd = useFocusCcd()
//   const [x, y] = useMouseCursorFocalPlaneCoord()

//   if (focusCcd && metadata) {
//     for (const amp of focusCcd.amps) {
//       const b = amp.bbox
//       if (includedInPolygon([x, y], [
//         [b.minx, b.miny],
//         [b.maxx, b.miny],
//         [b.maxx, b.maxy],
//         [b.minx, b.maxy]
//       ])) {
//         return amp
//       }
//     }
//   }
// }

// export function useFocusCcdFitsHeader() {
//   const shotId = useAppSelector(state => state.home.shotId)
//   const ccdMeta = useFocusCcd()
//   const { data, isFetching } = useShowFitsHeaderQuery({ shotId, ccdName: ccdMeta?.ccd_name ?? '' }, { skip: !ccdMeta })
//   return !isFetching ? data : undefined
// }
