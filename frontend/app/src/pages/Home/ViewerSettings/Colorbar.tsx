import { memo, useEffect, useRef } from "react"
import { RootState } from "../../../store"
import { useAppSelector } from "../../../store/hooks"

// 'optionA.csv': 'magma',
// 'optionB.csv': 'inferno',
// 'optionC.csv': 'plasma',
// 'optionD.csv': 'viridis',
// 'optionE.csv': 'cividis',
// 'optionF.csv': 'rocket',
// 'optionG.csv': 'mako',
// 'optionH.csv': 'turbo',
// 'viridis_map.csv': 'viridis',

import magma from '../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter/viridisLite/json/magma.json'
import inferno from '../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter/viridisLite/json/inferno.json'
import plasma from '../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter/viridisLite/json/plasma.json'
import viridis from '../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter/viridisLite/json/viridis.json'
import cividis from '../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter/viridisLite/json/cividis.json'
import rocket from '../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter/viridisLite/json/rocket.json'
import mako from '../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter/viridisLite/json/mako.json'
import turbo from '../../../StellarGlobe/Quicklook/QuicklookTileRenderer/ImaegFilter/viridisLite/json/turbo.json'
import { V3 } from "@stellar-globe/stellar-globe"

const colormaps = {
  Magma: magma,
  Inferno: inferno,
  Plasma: plasma,
  Viridis: viridis,
  Cividis: cividis,
  Rocket: rocket,
  Mako: mako,
  Turbo: turbo,
}


type Colormap = RootState['home']['filterParams']['colormap']


export function Colorbar() {
  const params = useAppSelector(state => state.home.filterParams)
  const colormap = params.colormap
  return <ColorbarRaw colormap={colormap} />
}




const ColorbarRaw = memo(({ colormap }: { colormap: Colormap }) => {
  const canvas = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    // @ts-ignore
    const cm:  V3[] = colormaps[colormap] ?? grayscale()
    const ctx = canvas.current?.getContext('2d')
    if (ctx) {
      const imageData = ctx.createImageData(16, 1)
      const data = imageData.data
      for (let i = 0; i < 16; i++) {
        const color = cm[Math.floor(i / 16 * cm.length)]
        data[i * 4 + 0] = color[0] * 255
        data[i * 4 + 1] = color[1] * 255
        data[i * 4 + 2] = color[2] * 255
        data[i * 4 + 3] = 255
      }
      ctx.putImageData(imageData, 0, 0)
    }
  }, [colormap])

  return (
    <canvas style={{ width: '100%', height: '20px', backgroundColor: '#007' }} width={16} height={1} ref={canvas} />
  )
})


function grayscale(): V3[] {
  const cm: V3[] = []
  const n = 256
  for (let i = 0; i < n; i++) {
    const v = i / (n - 1)
    cm.push([v, v, v])
  }
  return cm
}