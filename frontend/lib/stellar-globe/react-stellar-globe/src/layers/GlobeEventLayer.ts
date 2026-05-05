import { Globe, GlobeEventMap, Layer } from '@stellar-globe/stellar-globe'
import { memo, useCallback, useEffect } from "react"
import { setDisplayName, useLayerBind } from '../GlobeContext'
import { useInstanceVariable } from '../hooks/useInstanceVariable'


class GlobeEventLayer extends Layer { }


const eventNameMap = {
  onPointerDown: 'pointer-down',
  onPointerUp: 'pointer-up',
  onPointerMove: 'pointer-move',
  onCameraModeChange: 'camera-mode-change',
  onCameraMoveStart: 'camera-move-start',
  onCameraMove: 'camera-move',
  onCameraMoveEnd: 'camera-move-end',
  onImageLoaded: 'imageloadend',
  onResize: 'resize',
} as const


type GlobeEventMap$ = {
  [K in keyof typeof eventNameMap]: GlobeEventMap[(typeof eventNameMap)[K]]
}


type GlobeEventLayerProps = {
  [K in keyof typeof eventNameMap]: (event: GlobeEventMap$[K]) => void
}


const GlobeEventLayer$: React.FC<Partial<GlobeEventLayerProps>> = memo(props => {
  type PropName = keyof typeof eventNameMap

  const off = useInstanceVariable(() => new Map<PropName, () => void>())

  const rebind = (globe: Globe, pName: PropName) => {
    off.get(pName)?.()
    off.delete(pName)
    type Callback = undefined | ((event: GlobeEventMap[(typeof eventNameMap)[typeof pName]]) => void)
    const h = props[pName] as Callback
    if (h) {
      const _off = globe.on(eventNameMap[pName], h)
      off.set(pName, _off)
    }
  }

  const factory = useCallback(
    (globe: Globe) => {
      for (const pName of Object.keys(eventNameMap) as PropName[]) {
        rebind(globe, pName)
      }
      return new GlobeEventLayer(globe)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  const { node, ifLayerReady } = useLayerBind<GlobeEventLayer>(factory, true)

  for (const k of Object.keys(eventNameMap) as PropName[]) {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useEffect(
      () => {
        ifLayerReady(layer => rebind(layer.globe, k))
      },
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [props[k]],
    )
  }

  return node
})


setDisplayName({ GlobeEventLayer$ })
export { GlobeEventLayer$ }
