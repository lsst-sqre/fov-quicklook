import { Globe, PathLayer } from '@stellar-globe/stellar-globe'
import { memo, useCallback, useEffect } from 'react'
import { useLayerBind } from '..'
import { setDisplayName } from '../GlobeContext'


type PathLayerProps = ConstructorParameters<typeof PathLayer>[1] & {
  visible?: boolean
}

const PathLayer$: React.FC<PathLayerProps> = memo(props => {
  const { visible = true, ...options } = props
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const factory = useCallback((globe: Globe) => new PathLayer(globe, options), [])
  const { node, ifLayerReady } = useLayerBind<PathLayer>(factory, visible)
  const { paths, blendMode, dimOnZoom, darkenNarrowLine } = options

  useEffect(() => {
    ifLayerReady(layer => {
      layer.paths = paths
    })
  }, [ifLayerReady, paths])

  useEffect(() => {
    ifLayerReady(layer => {
      const defaults = PathLayer.defaultOptions()
      layer.blendeMode = blendMode ?? defaults.blendMode
      layer.dimOnZoom = dimOnZoom ?? defaults.dimOnZoom
      layer.darkenNarrowLine = darkenNarrowLine ?? defaults.darkenNarrowLine
    })
  }, [blendMode, darkenNarrowLine, dimOnZoom, ifLayerReady])

  return node
})

setDisplayName({ PathLayer$ })
export { PathLayer$ }
