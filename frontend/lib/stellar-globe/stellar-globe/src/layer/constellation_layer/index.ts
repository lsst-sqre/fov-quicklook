import { Globe } from "~/globe"
import { Layer } from "~/layer/layer"
import { overlayAlpha } from "~/layer/overlayAlpha"
import { SkyCoord } from "~/lib/angle"
import { BillboardImage, BillboardImageRef, BillboardRenderer } from "~/renderer/billboard_renderer"
import { Path, Renderer as PathRenderer } from "~/renderer/path_renderer"
import { V3, V4 } from "~/types"
import { text2imageData } from "~/utils/text2imagedata"
import { View } from "~/view"
import { constellationNamesHiragana, constellationNamesKanji } from "./japanese"
import { wegblProfile } from "~/devel/webgl-profiler/utils"


type ConstellationDictionary = { [name: string]: Constellation }


type Star = {
  ra: number,
  dec: number,
  b: string,
  hip: number,
  name: string,
  id: string,
}


type Constellation = {
  ecliptical: boolean,
  stars: Star[],
  lines: string[],
}


export type ConstellationLang = 'English' | 'Hiragana' | 'Kanji'


type Options = {
  showLines: boolean
  showNames: boolean
  lang: ConstellationLang
  fadeInDuration: number
  nameFont: string
  nameColor: string
}


export class ConstellationLayer extends Layer {
  static defaultOptions(): Options {
    return {
      showLines: true,
      showNames: false,
      lang: 'English',
      fadeInDuration: 400,
      nameFont: '12pt fantasy',
      nameColor: 'rgba(239, 225, 196, 1)',
    }
  }

  private pathRenderer?: PathRenderer
  private billboardRenderer?: BillboardRenderer
  private fadeInAlpha = 1
  private nameFont: string
  private nameColor: string

  showLines: boolean
  showNames: boolean
  readonly lang: ConstellationLang

  constructor(
    globe: Globe,
    _options: Partial<Options> = {},
  ) {
    super(globe)
    const options = { ...ConstellationLayer.defaultOptions(), ..._options }
    this.showLines = options.showLines
    this.showNames = options.showNames
    this.lang = options.lang
    this.nameFont = options.nameFont
    this.nameColor = options.nameColor
    this.addAnimation(({ r }) => {
      this.fadeInAlpha = r
    }, { duration: options.fadeInDuration })
    this.onRelease(() => {
      this.pathRenderer?.release()
      this.billboardRenderer?.release()
    })
  }

  render(view: View) {
    const alpha = this.fadeInAlpha * overlayAlpha(view)
    const gl = this.globe.gl
    if (this.showLines) {
      if (!this.pathRenderer) {
        this.pathRenderer = new PathRenderer(this.globe.gl)
        this.buildLines()
      }
      wegblProfile(gl, 'Constellation.lines', () => {
        this.pathRenderer!.render(view, alpha)
      })
    }
    if (this.showNames) {
      if (!this.billboardRenderer) {
        this.billboardRenderer = new BillboardRenderer(this.globe.gl)
        this.buildNameBillboards()
      }
      wegblProfile(gl, 'Constellation.names', () => {
        this.billboardRenderer!.render(view, alpha)
      })
    }
  }

  private async buildLines() {
    const constellations = await loadConstellations()
    const paths: Path[] = []

    for (const name of Object.keys(constellations)) {
      const c = constellations[name]
      const name2star = (() => {
        const m: { [name: string]: Star } = {}
        for (const star of c.stars) {
          m[star.name] = star
        }
        return m
      })()
      const color: V4 = c.ecliptical ? [1, 0.75, 0, 0.25] : [1, 1, 1, 0.25]
      for (const line of c.lines) {
        const stars = line.split('-').map((starName) => name2star[starName])
        for (let i = 0; i < stars.length - 1; ++i) {
          const path: Path = {
            points: [
              { position: star2xyz(stars[i]), color, size: 0.015 },
              { position: star2xyz(stars[i + 1]), color, size: 0.015 },
            ],
            close: false,
            joint: 'NONE',
          }
          paths.push(path)
        }
      }
    }
    this.pathRenderer!.setPaths(paths)
    this.globe.requestRefresh()
  }

  private async buildNameBillboards() {
    const constellations = await loadConstellations()
    const images: BillboardImage[] = []
    const imageRefs: BillboardImageRef[] = []
    for (const name of Object.keys(constellations)) {
      const c = constellations[name]
      imageRefs.push({
        imageID: images.length,
        position: centroid(c.stars),
        color: [1, 1, 1, 1],
      })
      const label = {
        English: name,
        Hiragana: constellationNamesHiragana[name],
        Kanji: constellationNamesKanji[name],
      }[this.lang]
      images.push({
        imageData: text2imageData(label, this.nameFont, this.nameColor),
        origin: [0, 0],
      })
    }
    this.billboardRenderer!.buildArray(images, imageRefs)
    this.globe.requestRefresh()
  }
}


function star2xyz(star: Star) {
  const coord = SkyCoord.fromDeg(star.ra, star.dec)
  return coord.xyz
}


function centroid(stars: Star[]) {
  let g: V3 = [0, 0, 0]
  for (const s of stars) {
    star2xyz(s).forEach((c, i) => g[i] += c)
  }
  g = g.map((c) => c / stars.length) as V3
  const r = Math.sqrt(g.reduce((sum, c) => sum + c * c, 0))
  return g.map((c) => c / r) as V3
}


async function loadConstellations(): Promise<ConstellationDictionary> {
  return (await import('./constellations.json')).default
}
