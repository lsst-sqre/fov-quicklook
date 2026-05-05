import { Globe, TextLayer, overlayAlpha } from "@stellar-globe/stellar-globe"
import { memo, useCallback, useEffect } from "react"
import { setDisplayName, useLayerBind } from "../GlobeContext"


type TextLayerProps = ConstructorParameters<typeof TextLayer>[1] & { visible?: boolean }


const TextLayer$: React.FC<TextLayerProps> = memo(props => {
  const { visible = true, ...options } = props
  const {
    defaultColor,
    defaultFont,
    texts,
    alphaFunc = overlayAlpha,
  } = options
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const factory = useCallback((globe: Globe) => new TextLayer(globe, options), [])
  const { node, ifLayerReady } = useLayerBind<TextLayer>(factory, visible)

  useEffect(() => {
    ifLayerReady(layer => {
      layer.update({
        texts,
        defaultColor: defaultColor ?? null,
        defaultFont: defaultColor ?? null,
      })
    })
  }, [ifLayerReady, texts, defaultColor, defaultFont])

  useEffect(() => {
    ifLayerReady(layer => {
      layer.alphaFunc = alphaFunc
      layer.globe.requestRefresh()
    })
  }, [alphaFunc, ifLayerReady])

  return node
})

setDisplayName({ TextLayer$ })

export { TextLayer$ }


export function alwaysOne() {
  return 1.
}
