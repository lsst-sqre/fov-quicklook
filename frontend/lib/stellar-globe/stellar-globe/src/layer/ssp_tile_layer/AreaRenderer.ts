import { Globe } from '~/globe'
import { path } from '~/index'
import { V3, V4 } from '~/types'
import { View } from '~/view'
import { overlayAlpha } from '../overlayAlpha'

type SingleBandArea = [number, number, number][][]
type MutliBandArea = { [filter: string]: SingleBandArea }
type Filter = { filterName: string, color: V3 }


export class AreaRenderer {
  private r: path.Renderer
  private region: MutliBandArea = {}
  private filters: Filter[] = []
  private alreadyReleased = false
  private fadeInAlpha = 0

  constructor(readonly globe: Globe, public baseUrl: string, filters: Filter[]) {
    this.r = new path.Renderer(globe.gl)
    this.r.minWidth = 3
    this.load().then(() => {
      globe.animations.add(({ r }) => {
        this.fadeInAlpha = r
      }, { duration: 1000 })
      this.setFilter(filters)
    })
  }

  release() {
    this.alreadyReleased = true
    this.r.release()
  }

  private async load() {
    const fail = { data: { '$any': [] } as MutliBandArea }
    this.region = convertToMultibandData(await (await fetch(`${this.baseUrl}/area.json`)).json().catch(_error => fail))
  }

  private rebuild() {
    if (this.alreadyReleased) {
      return
    }

    const width = 0.01
    const paths: path.Path[] = []

    for (const filter of this.filters) {
      const a = this.region[filter.filterName] || []
      const color: V4 = [...filter.color, 0.75]
      for (const piece of a) {
        const p: path.Path = { points: piece.map(v => ({ position: v, color, size: width })), close: true, joint: 'MITER' }
        paths.push(p)
      }
    }

    {
      const a = this.region['$any'] || []
      const color: V4 = Object.keys(this.region).length == 1 ? [0, 1, 0, 0.5] : [1, 1, 1, 0.25]
      for (const piece of a) {
        const p: path.Path = { points: piece.map(v => ({ position: v, color, size: width })), close: true, joint: 'MITER' }
        paths.push(p)
      }
    }

    this.r.setPaths(paths)
    this.globe.requestRefresh()
  }

  setFilter(filters: Filter[]) {
    this.filters = filters
    this.rebuild()
  }

  render(view: View, alpha = 1) {
    this.r.render(view, alpha * this.fadeInAlpha * overlayAlpha(view))
  }
}

function convertToMultibandData(raw: MutliBandArea | SingleBandArea): MutliBandArea {
  if (Array.isArray(raw)) {
    return { '$any': raw }
  }
  return raw
}
