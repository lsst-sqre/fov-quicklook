import { Globe, TractTileLayer } from "@stellar-globe/stellar-globe"
import React, { memo, useCallback, useEffect } from "react"
import { mountOndemand, setDisplayName, useLayerBind } from "../GlobeContext"


type TractTileLayerProps = ConstructorParameters<typeof TractTileLayer>[1] & {
  visible?: boolean
  filterNameDictionary?: filterNameDictionary
}

type ColorParams = NonNullable<TractTileLayerProps['colorParams']>

const TractTileLayer$: React.FC<TractTileLayerProps> = mountOndemand(memo(props => {
  const {
    baseUrl,
    colorParams = TractTileLayer.defaultParams({ type: 'sdssTrueColor' }),
    outline = false,
    visible = true,
    magFilter = 'linear',
    filterNameDictionary,
  } = props
  const factory = useCallback(
    (globe: Globe) => {
      return new TractTileLayer(globe, {
        ...props,
        colorParams: applyFilterNameTranslation(colorParams, filterNameDictionary)
      })
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [baseUrl],
  )
  const { node, ifLayerReady } = useLayerBind<TractTileLayer>(factory, visible)

  useEffect(() => {
    ifLayerReady(layer => {
      layer.outline = outline
      layer.globe.requestRefresh()
    })
  }, [ifLayerReady, outline])

  useEffect(() => {
    ifLayerReady(layer => {
      layer.setParams(applyFilterNameTranslation(colorParams, filterNameDictionary))
    })
  }, [colorParams, filterNameDictionary, ifLayerReady])

  useEffect(() => {
    ifLayerReady(layer => {
      layer.setMagFilter(magFilter)
    })
  }, [ifLayerReady, magFilter])

  return node
}), 'visible')
setDisplayName({ TractTileLayer$ })
export { TractTileLayer$ }


type filterNameDictionary = { [altName: string]: string }


function applyFilterNameTranslation(colorParams: ColorParams, dict: filterNameDictionary | undefined) {
  if (dict) {
    const filters = colorParams.filters.map(f => {
      // if (dict[f] === undefined) {
      //   throw new Error(`Filter name lookup failed: ${f} for ${JSON.stringify(dict)}`)
      // }
      return dict[f] ?? f
    })
    return { ...colorParams, filters }
  }
  return colorParams
}
