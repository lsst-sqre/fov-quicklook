import { useLayerBind } from "@stellar-globe/react-stellar-globe"
import { Globe, Layer, V2, View } from "@stellar-globe/stellar-globe"
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from "react"
import { QuicklookMetadata } from "../../store/api/openapi"
import { QuicklookRenderer } from "./QuicklookTileRenderer"
import { RubinImageFilterParams } from "./QuicklookTileRenderer/ImaegFilter"


class QuicklookLayer extends Layer {
  r: QuicklookRenderer

  constructor(
    globe: Globe,
    metadata: QuicklookMetadata,
    filterParams: RubinImageFilterParams,
  ) {
    super(globe)
    this.r = new QuicklookRenderer(globe, metadata, filterParams)
  }

  render(view: View): void {
    this.r.render(view)
  }

  pixelValue(pixelCoords: V2) {
    return this.r.pixelValue(pixelCoords)
  }
}

type QuicklookProps = {
  visible?: boolean
  metadata: QuicklookMetadata
  filterParams: RubinImageFilterParams
}


export type QuicklookHandle = {
  layer: () => QuicklookLayer | undefined,
}


export const Quicklook$ = forwardRef<QuicklookHandle, QuicklookProps>(({
  visible = true,
  metadata,
  filterParams,
}, ref) => {
  const layerRef = useRef<QuicklookLayer>()

  useImperativeHandle(ref, () => ({
    layer: () => layerRef.current
  }))

  const factory = useCallback(
    (globe: Globe) => {
      const layer = new QuicklookLayer(globe, metadata, filterParams)
      layerRef.current = layer
      return layer
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [metadata],
  )
  const { node, ifLayerReady } = useLayerBind<QuicklookLayer>(factory, visible)
  useEffect(() => {
    ifLayerReady(layer => {
      layer.r.setFilterParams(filterParams)
    })
  }, [filterParams, ifLayerReady])
  return node
})
