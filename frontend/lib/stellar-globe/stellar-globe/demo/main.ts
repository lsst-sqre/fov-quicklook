import { ClickableMarkerLayer } from '~/layer/marker_layer'
import { BeautifulObjectLayer, ConstellationLayer, EsoMilkyWayLayer, Globe, GridLayer, HipparcosCatalogLayer, Layer, SspTileLayer, V4, View, angle, hips, triangleStrip } from '../src'
import { SkyCoord, dms2deg } from '../src/lib/angle'
import { zenithSkyCoord } from '../src/utils/date'
// import { ClicakblePolygonLayer } from './ClickablePolygonLayer'
import { MarkerType, markerTypes } from '~/layer/marker_layer/marker'
import './style.scss'


window.addEventListener('load', main)


function main() {
  // // @ts-expect-error
  const hipsUrl = '//alasky.cds.unistra.fr/Pan-STARRS/DR1/color-i-r-g'
  // const baseUrl = '//alasky.cds.unistra.fr/DSS/DSSColor'
  // const baseUrl = '//hscmap.mtk.nao.ac.jp/hscMap4/misc/hips/gaia'

  const el = document.createElement('div')
  document.body.appendChild(el)
  el.style.width = '100vw'
  el.style.height = '100vh'

  // @ts-expect-error
  const zenith = zenithSkyCoord({ when: new Date, where: NaojLocation })
  // const globe = new Globe(el, { viewOptions: { retina: false, ...zenith } })
  const globe = new Globe(el, { viewOptions: { retina: true } })

  // if (webglProfileSupported()) {
  //   const profiler = enableWebglProfiler(globe.gl)
  //   setTimeout(() => {
  //     const stop = profiler.start()
  //     setTimeout(() => {
  //       stop()
  //     }, 3000)
  //   }, 2000)
  // }

  initTileLayer(globe)
  globe.addNewLayer(GridLayer)
  globe.addNewLayer(HipparcosCatalogLayer)
  globe.addNewLayer(ConstellationLayer, { showLines: true, showNames: false, lang: 'English' })
  globe.addNewLayer(hips.SimpleImageLayer, hipsUrl)
  globe.addNewLayer(BeautifulObjectLayer, 'm31')
  globe.addNewLayer(EsoMilkyWayLayer)
  // globe.addNewLayer(SspTileLayer, { baseUrl: '//hscmap.mtk.nao.ac.jp/hscMap4/data/la2016', outline: true })

  globe.addNewLayer(ClickableMarkerLayer, {
    markers: Array.from({ length: 1000 }, (_, i) => ({
      position: SkyCoord.fromDeg(randomInRange(-1, 1), randomInRange(-1, 1)).xyz,
      color: [...hsvToRgb(Math.random(), 0.75, 1), 0.75] as V4,
      type: markerTypes[i % markerTypes.length] as MarkerType,
    })),
    defaultColor: [1, 1, 1, 0],
    defaultType: 'circle',
    dimmAlpha: 0.75,
    onClick: (i) => console.log(i)
  })

  globe.addNewLayer(TriangleStirpLayer)
}



function initTileLayer(globe: Globe) {
  const betaInput = document.querySelector('#beta-input') as HTMLInputElement
  const params = SspTileLayer.defaultParams({ type: 'simpleRgb' })
  const a = 1.e+1
  const f = (x: number) => Math.exp(a * x)
  const g = (y: number) => Math.log(y) / a
  const layer = globe.addNewLayer(SspTileLayer, { baseUrl: '//hscmap.mtk.nao.ac.jp/hscMap4/data/pdr3_wide', outline: true, colorParams: params })
  SspTileLayer.assertType(params, 'simpleRgb')
  betaInput.addEventListener('input', e => {
    // @ts-ignore
    const beta = f(Number(e.currentTarget.value))
    params.simpleRgb.beta = beta
    layer.setParams(params)
  })
  betaInput.value = String(g(params.simpleRgb.beta))
}


const NaojLocation = { lat: angle.dms2deg('35:40:30.7'), lon: dms2deg('139:32:16.2') }


// @ts-ignore
class TriangleStirpLayer extends Layer {
  private r!: triangleStrip.Renderer

  constructor(globe: Globe) {
    super(globe)
    this.r = new triangleStrip.Renderer(globe.gl)
    this.onRelease(() => this.r.release())
    this.setupTriangles()
  }

  private setupTriangles() {
    this.r.addStrips([
      { position: [0, 0, 0], color: [0, 0, 0, 1] },
      { position: [1, 0, 0], color: [1, 0, 0, 1] },
      { position: [0, 1, 0], color: [0, 1, 0, 1] },
      { position: [1, 1, 0], color: [1, 1, 0, 1] },
    ])
    this.r.addStrips([
      { position: [0, 0, 0], color: [0, 0, 0, 1] },
      { position: [0, 1, 0], color: [1, 0, 0, 1] },
      { position: [0, 0, 1], color: [0, 1, 0, 1] },
      { position: [0, 1, 1], color: [1, 1, 0, 1] },
    ])

    const a = 1.e-2
    for (let i = 0; i < 10000; ++i) {
      const R = () => -1 + 2 * Math.random()
      const [x, y, z] = [R(), R(), R()]
      const c0: V4 = [1, 0, 0, 1]
      const c1: V4 = [0, 1, 0, 1]
      const c2: V4 = [0, 0, 1, 1]
      this.r.addTriangle(
        { position: [x + a * R(), y + a * R(), z + a * R()], color: c0 },
        { position: [x + a * R(), y + a * R(), z + a * R()], color: c1 },
        { position: [x + a * R(), y + a * R(), z + a * R()], color: c2 },
      )
    }
  }

  render(view: View) {
    this.r.render(view)
  }
}


function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  let r: number, g: number, b: number

  let i = Math.floor(h * 6)
  let f = h * 6 - i
  let p = v * (1 - s)
  let q = v * (1 - f * s)
  let t = v * (1 - (1 - f) * s)

  switch (i % 6) {
    case 0: r = v, g = t, b = p; break
    case 1: r = q, g = v, b = p; break
    case 2: r = p, g = v, b = t; break
    case 3: r = p, g = q, b = v; break
    case 4: r = t, g = p, b = v; break
    case 5: r = v, g = p, b = q; break
  }

  // @ts-ignore
  return [r, g, b]
}

function randomInRange(min: number, max: number) {
  return (max - min) * Math.random() + min
}
