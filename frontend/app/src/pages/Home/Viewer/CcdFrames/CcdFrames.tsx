import { useLayerBind } from "@stellar-globe/react-stellar-globe"
import { Globe } from "@stellar-globe/stellar-globe"
import React, { memo, useCallback, useEffect } from "react"
import { useQuicklookStatus } from "../../context/quicklook"
import { useFocusedAmp, useFocusedCcd, useWcs } from "../../hooks"
import { BBoxLayer } from "./BBoxLayer"
import { useAppSelector } from "../../../../store/hooks"


const CcdFrameLayer$: React.FC = memo(() => {
  const { metadata } = useQuicklookStatus()
  const factory = useCallback((globe: Globe) => {
    const layer = new BBoxLayer(globe, [0, 0, 1, 0.2])
    return layer
  }, [])
  const { node, ifLayerReady } = useLayerBind<BBoxLayer>(factory, !!metadata)
  const wcs = useWcs()

  useEffect(() => {
    ifLayerReady(layer => {
      if (metadata?.ccd_meta && wcs) {
        layer.update(metadata.ccd_meta.map(r => r.bbox).flat(), wcs)
      }
    })
  }, [ifLayerReady, metadata, wcs])

  return node
})


const FocusedCcd$: React.FC = memo(() => {
  const factory = useCallback((globe: Globe) => {
    const layer = new BBoxLayer(globe, [0, 1, 1, 0.25])
    return layer
  }, [])
  const focusedCcd = useFocusedCcd()
  const { node, ifLayerReady } = useLayerBind<BBoxLayer>(factory, !!focusedCcd)
  const wcs = useWcs()

  useEffect(() => {
    ifLayerReady(layer => {
      if (wcs && focusedCcd) {
        layer.update([focusedCcd.bbox, ...focusedCcd.amps.map(a => a.bbox)], wcs)
      }
    })
  }, [focusedCcd, ifLayerReady, wcs])

  return node
})


const FocusedAmp$: React.FC = memo(() => {
  const factory = useCallback((globe: Globe) => {
    const layer = new BBoxLayer(globe, [0, 1, 1, 0.75])
    return layer
  }, [])
  const focusedAmp = useFocusedAmp()
  const { node, ifLayerReady } = useLayerBind<BBoxLayer>(factory, !!focusedAmp)
  const wcs = useWcs()

  useEffect(() => {
    ifLayerReady(layer => {
      if (wcs && focusedAmp) {
        layer.update([focusedAmp.bbox], wcs)
      }
    })
  }, [focusedAmp, ifLayerReady, wcs])

  return node
})


export function CcdFrames() {
  return (
    <>
      <CcdFrameLayer$ />
      <FocusedCcd$ />
      <FocusedAmp$ />
    </>
  )
}



export const HighlitedCcds: React.FC = memo(() => {
  const factory = useCallback((globe: Globe) => {
    const layer = new BBoxLayer(globe, [1, 0, 1, 1])
    return layer
  }, [])
  const { metadata } = useQuicklookStatus()
  const { node, ifLayerReady } = useLayerBind<BBoxLayer>(factory, !!metadata)
  const ccds = useAppSelector(state => state.home.hilightedCcdId)
  const wcs = useWcs()

  useEffect(() => {
    ifLayerReady(layer => {
      if (metadata?.ccd_meta && wcs) {
        layer.update(metadata.ccd_meta.filter(c => ccds.includes(c.ccd_id.ccd_name)).map(r => r.bbox).flat(), wcs)
      }
    })
  }, [ccds, ifLayerReady, metadata, wcs])

  return node
})
