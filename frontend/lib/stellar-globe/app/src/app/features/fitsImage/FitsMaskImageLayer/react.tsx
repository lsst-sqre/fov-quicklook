import { useLayerBind } from "@stellar-globe/react-stellar-globe"
import { Globe, V4, fits } from "@stellar-globe/stellar-globe"
import { memo, useCallback, useEffect, useState } from "react"
import { FitsMaskImageLayer, MaskMapMeta } from "."
import { useIsMounted } from "../../../../common/hooks/useIsMounted"


type Props = {
  url: string
  visible?: boolean
  maskBit: number
  color: V4
}

type Meta = MaskMapMeta


export function FitsImageLayer$(props: Props) {
  const isMounted = useIsMounted()
  const { url } = props
  const [cache, setCache] = useState<Meta | undefined>()
  useEffect(() => {
    (async () => {
      const meta = await (await fetch(`${url}/meta.json`)).json() as Meta
      if (isMounted() && url === props.url) {
        setCache(meta)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.url, url])
  if (cache) {
    return <SafeFitsMaskImageLayer visible={props.visible} meta={cache} maskBit={props.maskBit} color={props.color} baseUrl={url} />
  }
}


function find2dHdu(hdul: fits.Hdu[]) {
  return 0
  for (let i = 0; i < hdul.length; ++i) {
    try {
      if (hdul[i].card('NAXIS', 'number') === 2) {
        return i
      }
    }
    catch {
      continue
    }
  }
  return -1
}


const SafeFitsMaskImageLayer: React.FC<{
  meta: Meta,
  visible?: boolean
  maskBit: number
  color: V4
  baseUrl: string
}> = memo(({ meta, color, maskBit, baseUrl, visible = true }) => {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const factory = useCallback((globe: Globe) => new FitsMaskImageLayer(globe, { meta, color, maskBit, baseUrl }), [maskBit, baseUrl])
  const { node, ifLayerReady } = useLayerBind<FitsMaskImageLayer>(factory, visible)
  useEffect(() => {
    ifLayerReady(layer => {
      layer.changeColor(color)
    })
  }, [color, ifLayerReady])
  return node
})
