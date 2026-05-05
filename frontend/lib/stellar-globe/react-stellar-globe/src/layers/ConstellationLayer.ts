import { ConstellationLayer, Globe } from "@stellar-globe/stellar-globe"
import React, { memo, useCallback, useEffect } from "react"
import { setDisplayName, useLayerBind } from "../GlobeContext"


type ConstellationLayerProps = NonNullable<ConstructorParameters<typeof ConstellationLayer>[1]> & { visible?: boolean }

const ConstellationLayer$: React.FC<ConstellationLayerProps> = memo(props => {
  const { visible = true, ...options } = { ...ConstellationLayer.defaultOptions(), ...props }
  const {
    lang, nameColor, nameFont, showLines, showNames,
  } = options
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const factory = useCallback((globe: Globe) => new ConstellationLayer(globe, options), [lang, nameColor, nameFont])
  const { node, ifLayerReady } = useLayerBind<ConstellationLayer>(factory, visible)

  useEffect(() => {
    ifLayerReady(layer => {
      layer.showLines = showLines
      layer.showNames = showNames
      layer.globe.requestRefresh()
    })
  }, [ifLayerReady, showLines, showNames])

  return node
})

setDisplayName({ ConstellationLayer$ })

export { ConstellationLayer$ }
